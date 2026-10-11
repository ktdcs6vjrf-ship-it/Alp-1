/* Desk « Recherche & dév » : la stratégie de scalp « Mur », à connaître par cœur ; douze exemples à la heatmap dont
   l’issue est calculée sur le chemin dessiné ; un testeur en un geste ; et ce que disent les études sur la liquidité
   affichée, avec leurs sources. Outils de l’utilisateur : un téléphone et le direct YouTube de Bookmap.
   Rien n’y suppose un avantage : sans dérive, un objectif à 2R avant un stop à 1R tombe une fois sur trois. */
var h = T.h, U = T.ui, F = T.fmt;
T.lib = T.lib || {};
var R = T.lib.rnd = {};
var K = { log: 'rnd:mode', side: 'rnd:side', view: 'rnd:vue' };
function fin(v) { return typeof v === 'number' && isFinite(v); }
R.SETUP = 'Scalp Mur';

/* =====================================================================
   1. La carte : six mots, quatre interdits
   ===================================================================== */
R.MOTS = [
  { m: 'Sens', t: 'Le côté de la VWAP décide.', s: 'Prix au-dessus de la VWAP : achats seulement. En dessous : ventes seulement. Sur la VWAP : rien.' },
  { m: 'Mur', t: 'Un mur ancien, du bon côté.', s: 'Une ligne de liquidité nette sur la heatmap, là depuis au moins deux minutes : sous le prix pour un achat, au-dessus pour une vente.' },
  { m: 'Espace', t: 'De la place pour 2R.', s: 'Aucun autre mur entre ton entrée et ton objectif. Sinon l’objectif est bloqué d’avance.' },
  { m: 'Touche', t: 'Ordre limite devant le mur.', s: 'Un point devant le mur (au-dessus pour un achat). Le prix vient à toi, tu ne cours pas après.' },
  { m: 'Tient', t: 'Il échange et ne fond pas.', s: 'Des bulles s’impriment sur le mur et sa taille tient : tu restes. Le mur disparaît ou fond : tu sors tout de suite.' },
  { m: 'Sortie', t: 'Stop derrière, 2R devant, 3 minutes.', s: 'Stop trois points derrière le mur ; objectif à deux fois le risque ; au bout de trois minutes, sortie au marché.' }
];
R.INTERDITS = [
  { t: 'Annonce de rang 1', s: 'De cinq minutes avant à un quart d’heure après.' },
  { t: 'Ouverture américaine', s: 'De 15 h 30 à 15 h 35, heure de Paris : les murs s’y posent et s’y retirent en rafale.' },
  { t: 'Mur de moins de deux minutes', s: 'Un mur qui surgit au dernier moment est la forme des ordres de manipulation sanctionnés sur le CME.' },
  { t: 'Retard du flux au-delà de 5 s', s: 'Compare l’heure du direct à celle de ton téléphone. Au-delà, tu trades le passé.' }
];

/* =====================================================================
   2. Le calcul : coûts, point mort, loi nulle, échantillon
   ===================================================================== */
/* Coût d’un aller-retour : commission + un tick de glissement par jambe (déclaré). */
R.cout = function (set) { return set.commissionRT + 2 * set.tick * set.pointValue; };
/* Point mort d’un trade à 1:rr : p·rr·R − (1 − p)·R − C = 0 → p = (R + C)/((1 + rr)·R). */
R.pointMort = function (stopPts, rr, set) { var Rd = stopPts * set.pointValue, C = R.cout(set); return Rd > 0 ? (Rd + C) / ((1 + rr) * Rd) : NaN; };
R.STOPS = [1, 2, 3, 4, 6, 8, 12];
R.tableCouts = function (set, rr) { return R.STOPS.map(function (s) { var Rd = s * set.pointValue, C = R.cout(set); return { stop: s, risque: Rd, part: C / Rd, pm: R.pointMort(s, rr, set) }; }); };
/* Le plus petit stop (en points) dont les coûts pèsent au plus 20 % du risque : déclaré. */
R.stopMinimal = function (set, part) { return R.cout(set) / ((part || 0.2) * set.pointValue); };
/* Loi nulle : sans dérive, 2R avant 1R arrive une fois sur trois (arrêt optionnel, a/(a+b)). */
R.LOI_NULLE = 1 / 3;
/* Trades pour distinguer un taux p1 du point mort p0, test unilatéral à 5 %, puissance 80 %. L’effet est DÉCLARÉ
   (cinq points au-dessus du point mort), jamais tiré du taux observé. */
R.EFFET = 0.05;
R.tradesPourPreuve = function (p0, effet) { var p1 = p0 + (effet || R.EFFET), za = 1.6449, zb = 0.8416; return Math.ceil(Math.pow((za * Math.sqrt(p0 * (1 - p0)) + zb * Math.sqrt(p1 * (1 - p1))) / (p1 - p0), 2)); };

/* =====================================================================
   3. Le testeur : les trades de scalp au journal, setup « Scalp Mur »
   ===================================================================== */
R.ISSUES = [
  { id: 'gain', label: '+2R', r: 2, tone: 'acc' },
  { id: 'perte', label: '−1R', r: -1 },
  { id: 'sortie', label: 'Sortie mur', r: -0.25 },
  { id: 'temps', label: '3 min', r: 0 }
];
R.entree = function (issue, side, at, instrument) {
  var i = R.ISSUES.filter(function (x) { return x.id === issue; })[0];
  return { kind: 'pris', side: side, setup: R.SETUP, status: 'clos', closedAt: at, at: at, r: i.r, fin: issue === 'gain' ? 'objectif' : issue === 'perte' ? 'stop' : issue === 'temps' ? 'cloche' : 'invalidation', plan: true, instrument: instrument, note: 'Inscrit depuis le testeur Scalp Mur' + (issue === 'sortie' || issue === 'temps' ? ' : R estimé, à corriger au journal.' : '.') };
};
R.refus = function (at) { return { kind: 'refus', stage: 'declencheur', setup: R.SETUP, at: at }; };
R.stats = function (rows) {
  var t = (rows || []).filter(function (x) { return x && x.kind === 'pris' && x.setup === R.SETUP && fin(x.r); }).sort(function (a, b) { return a.at - b.at; });
  var n = t.length, g = t.filter(function (x) { return x.r > 0; }).length, sum = t.reduce(function (a, x) { return a + x.r; }, 0), eq = [], c = 0;
  t.forEach(function (x, i) { c += x.r; eq.push([i + 1, c]); });
  var passes = (rows || []).filter(function (x) { return x && x.kind === 'refus' && x.setup === R.SETUP; }).length;
  return { n: n, gains: g, wr: n ? g / n : NaN, moyR: n ? sum / n : NaN, totalR: sum, eq: eq, passes: passes };
};

/* =====================================================================
   4. Les études : ce qui est établi, ce qui ne l’est pas
   ===================================================================== */
R.ETUDES = [
  { q: 'Une liquidité qui apparaît d’un coup sur une zone clé sert à faire peur, puis disparaît.', v: 'établi', vt: 'Établi que cela existe. Pas établi que tu puisses en profiter.',
    p: ['Sur le CME, la CFTC a décrit un algorithme qui posait quatre à six très gros ordres de vente juste au-dessus du meilleur prix, pour être vus sans être exécutés, pendant plus de deux heures avant le krach éclair du 6 mai 2010 (Sarao, E-mini S&P 500). Plaidé coupable ; condamné en 2020.',
      'Premier jugement pénal sous la loi Dodd-Frank (Coscia, 2015, contrats du CME) : de gros ordres d’un côté, posés pour déplacer le prix, retirés avant exécution, pendant qu’un petit ordre attendait de l’autre côté. Confirmé en appel.',
      'JPMorgan a payé 920,2 millions de dollars en 2020 pour la même pratique sur les métaux et les Treasuries, de 2008 à 2016.',
      'Sur données complètes de la bourse de Corée, Lee, Eom et Park (2013) montrent que ces ordres, presque jamais exécutés, créaient l’impression d’un déséquilibre du carnet pour déplacer les prix, et rapportaient à leurs auteurs. Leur fréquence a chuté quand la bourse a changé ses règles d’affichage.',
      'Hasbrouck et Saar (2009) : une large part des ordres limites est annulée dans les deux secondes.'],
    implication: 'Le mur qui surgit au dernier moment est souvent fait pour ne pas être touché. Il ne protège aucun stop. Règle du plan : seul compte un mur présent depuis plusieurs minutes, qui échange au contact.',
    src: [['CFTC c. Sarao (2015)', 'https://www.cftc.gov/PressRoom/PressReleases/pr7156-15'], ['Sarao, condamnation (2020)', 'https://www.bnnbloomberg.ca/trader-blamed-for-2010-flash-crash-gets-no-jail-for-spoofing-1.1381078'], ['Coscia, premier jugement (2015)', 'https://morganlewis.com/pubs/2015/11/prosecutors-record-first-ever-conviction-for-spoofing'], ['JPMorgan, 920 M$ (2020)', 'https://www.americanbanker.com/articles/jpmorgan-pays-920-million-admits-misconduct-over-spoofing'], ['Lee, Eom et Park (2013)', 'https://ideas.repec.org/a/eee/finmar/v16y2013i2p227-252.html'], ['Hasbrouck et Saar (2009)', 'https://ideas.repec.org/a/eee/finmar/v12y2009i2p143-172.html']] },
  { q: 'Une liquidité durable, qui grossit quand on s’en approche, sert de vrai support ou de vraie résistance.', v: 'partiel', vt: 'Partiellement établi. La rentabilité d’un rebond, non.',
    p: ['Kavajecz et Odders-White (2004) : les niveaux de support et de résistance coïncident avec des pics de profondeur du carnet d’ordres. Les niveaux que l’analyse technique trace sont là où la liquidité est déjà posée.',
      'Tóth, Bouchaud et coauteurs (2011) : l’essentiel de la liquidité est latent ; il ne s’affiche qu’à mesure que le prix s’approche. Une liquidité qui grossit à l’approche est donc le comportement normal du carnet, pas un signe en soi.',
      'Cao, Hansch et Wang (2009) : la profondeur au-delà du meilleur prix porte environ 22 % de la découverte du prix ; les déséquilibres le long du carnet sont liés aux rendements de très court terme.'],
    implication: 'Un mur ancien sur un niveau tracé est un endroit où le prix a des raisons de ralentir. Aucune de ces études ne dit qu’un achat à son contact gagne plus souvent qu’une fois sur trois à 1:2 après coûts. C’est ce que le testeur doit mesurer.',
    src: [['Kavajecz et Odders-White (2004)', 'https://ideas.repec.org/a/oup/rfinst/v17y2004i4p1043-1071.html'], ['Tóth et al. (2011)', 'https://www.arxiv.org/abs/1105.1694v3'], ['Cao, Hansch et Wang (2009)', 'https://ideas.repec.org/a/wly/jfutmk/v29y2009i1p16-41.html']] },
  { q: 'La liquidité de court terme sert d’aimant.', v: 'indirect', vt: 'Indirect. Ce qui attire n’est pas ce que la heatmap montre.',
    p: ['Osler (2003, Journal of Finance) : les ordres de prise de bénéfice se regroupent sur les chiffres ronds, et le prix y rebrousse chemin plus souvent ; les ordres stop se regroupent juste au-delà.',
      'Osler (2005) : quand le prix atteint un amas de stops, le mouvement s’accélère (cascade) : les stops déclenchés achètent ou vendent au marché, dans le sens du mouvement.',
      'Les ordres stop ne s’affichent pas dans le carnet du CME. Une heatmap montre les ordres limites posés, pas les stops.'],
    implication: 'L’« aimant » documenté est un amas de stops invisible au-delà d’un niveau évident (chiffre rond, sommet de la veille), qui accélère une cassure. Un mur visible n’est pas établi comme aimant. Dans le plan, on ne trade pas l’aimant.',
    src: [['Osler (2003)', 'https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr125.html'], ['Osler (2005)', 'https://ideas.repec.org:443/p/fip/fednsr/150.html']] },
  { q: 'Le déséquilibre du carnet prédit le prochain mouvement.', v: 'établi', vt: 'Établi, à l’échelle du tick et de la seconde.',
    p: ['Cont, Kukanov et Stoikov (2014) : sur de courts intervalles, les variations de prix s’expliquent surtout par le déséquilibre du flux d’ordres aux meilleurs prix, avec une pente inversement proportionnelle à la profondeur.',
      'Gould et Bonart (2016) : le déséquilibre des files au meilleur prix prédit le sens du prochain mouvement d’un tick, nettement mieux pour les actifs à gros tick.'],
    implication: 'L’horizon de ces résultats est la seconde, celui des algorithmes colocalisés. Depuis un direct YouTube, ce signal est déjà dans le prix quand tu le vois.',
    src: [['Cont, Kukanov et Stoikov (2014)', 'https://arxiv.org/abs/1011.6402'], ['Gould et Bonart (2016)', 'https://arxiv.org/pdf/1512.03492']] },
  { q: 'On peut scalper dix secondes à partir du direct YouTube de Bookmap.', v: 'non', vt: 'Non : le direct a du retard.',
    p: ['YouTube indique qu’en mode faible latence la plupart des spectateurs ont moins de dix secondes de retard, et moins de cinq en latence ultra-faible ; le mode normal en a davantage. Le mode est choisi par la chaîne, pas par toi.'],
    implication: 'Un trade de dix secondes est fini avant que tu le voies. Le plan ne lit donc que ce qui dure : des murs présents depuis deux minutes, des tenues d’au moins trente secondes. Mesure ton retard avant chaque séance.',
    src: [['YouTube : latence d’un direct', 'https://support.google.com/youtube/answer/7444635']] }
];
R.VERDICTS = { 'établi': 'Établi', partiel: 'Partiel', indirect: 'Indirect', non: 'Non' };

/* =====================================================================
   5. Interface
   ===================================================================== */
var CSS = '.rd-mots{display:grid;gap:8px}.rd-mot{display:grid;grid-template-columns:auto minmax(0,1fr);gap:2px 14px;align-items:baseline;padding:12px 14px;border:1px solid var(--line);border-radius:var(--r);background:var(--panel)}' +
  '.rd-mot b{grid-row:span 2;font:600 22px/1 var(--f-sans);letter-spacing:-.02em;color:var(--hi);min-width:4.6em}.rd-mot b i{font:600 11px var(--f-mono);font-style:normal;color:var(--violet-2);margin-right:8px}.rd-mot strong{color:var(--fg);font-size:14px}.rd-mot span{color:var(--soft);font-size:12.5px;line-height:1.45}' +
  '.rd-hero{font:600 15px/1.5 var(--f-mono);letter-spacing:.06em;color:var(--violet-2);text-transform:uppercase;padding:14px;border:1px solid var(--violet-b);border-radius:var(--r);background:var(--violet-a);text-align:center}' +
  '.rd-ex{display:grid;gap:12px}@media(min-width:900px){.rd-ex{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}}' +
  '.rd-res{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.rd-res b{font:600 13px var(--f-mono);color:var(--hi)}' +
  '.rd-log{display:grid;grid-template-columns:1fr 1fr;gap:8px}.rd-log .btn{height:auto;min-height:58px;font-size:17px;justify-content:center}.rd-log .wide{grid-column:1/-1;min-height:46px;font-size:14px}' +
  '.rd-et{display:flex;flex-direction:column;gap:8px}.rd-et ul{margin:0;padding-left:18px;display:grid;gap:6px}.rd-et li{font-size:13px;line-height:1.5;color:var(--fg)}.rd-src{display:flex;flex-wrap:wrap;gap:6px 12px;font-size:12px}.rd-src a{color:var(--violet-2)}';
function injectCss() { if (document.getElementById('rnd-css')) return; var s = document.createElement('style'); s.id = 'rnd-css'; s.textContent = CSS; document.head.appendChild(s); }
function PF() { return T.lib.planFig; }
function svgBox(svg) { var d = h('div', { class: 'pl-fig' }); d.innerHTML = svg; return d; }
function badge(issue) { var ok = issue === 'gain'; return h('div', { class: 'pl-badge' + (ok ? ' ok' : '') }, { gain: 'Gain : +2R', perte: 'Perte : −1R', sortie: 'Sortie avant le stop', temps: 'Sortie au temps', refus: 'Pas de trade', rien: 'Pas rempli' }[issue] || issue); }
function exemple(key) {
  var G = PF(), c = G.SCALP[key], tr = G.scalpTrade(key);
  var res = tr.issue === 'refus' ? 'Refusé : ' + tr.why + '.' : tr.issue === 'rien' ? 'Pas d’exécution : ' + tr.why + '.' : 'Résultat calculé : ' + (tr.r > 0 ? '+' : tr.r < 0 ? '−' : '') + F.num(Math.abs(tr.r), 2) + ' R (' + tr.why + ').';
  return U.card({ title: c.t, accent: tr.issue === 'gain', body: [badge(tr.issue), svgBox(G.scalpSvg(key)), h('p', null, c.lire), h('div', { class: 'rd-res' }, h('b', null, res)), h('p', { class: 'pl-ill' }, 'Le résultat n’est pas écrit : il est calculé en appliquant les six règles au chemin dessiné. Violet : entrée. Pointillé gris : stop. Pointillé blanc : 2R. ' + G.DISCLAIMER)] });
}

function renderCarte(root, ctx) {
  var set = ctx.settings;
  root.appendChild(h('div', { class: 'rd-hero' }, R.MOTS.map(function (x) { return x.m; }).join(' · ')));
  var s1 = U.section('Les six *mots*', 'à savoir par cœur');
  s1.appendChild(h('div', { class: 'rd-mots' }, R.MOTS.map(function (x, i) { return h('div', { class: 'rd-mot' }, h('b', null, h('i', null, String(i + 1)), x.m), h('strong', null, x.t), h('span', null, x.s)); })));
  root.appendChild(s1);
  var s2 = U.section('Quatre *interdits*', 'ils passent avant tout');
  s2.appendChild(h('ol', { class: 'pl-ord' }, R.INTERDITS.map(function (x) { return h('li', null, h('b', null, x.t), h('span', null, x.s)); })));
  root.appendChild(s2);
  var s3 = U.section('À quoi *ça ressemble*', 'le cas qui paie');
  s3.appendChild(exemple('tient'));
  s3.appendChild(U.button({ label: 'Voir les douze exemples ›', kind: 'ghost', onClick: function () { ctx.setTab('exemples'); } }));
  root.appendChild(s3);
  var s4 = U.section('Avant de *commencer*', '30 secondes');
  s4.appendChild(h('ol', { class: 'pl-ord' }, [
    ['Ouvre le direct Bookmap', 'Le NQ, la heatmap en grand. Repère les lignes claires qui durent : ce sont les murs.'],
    ['Mesure le retard', 'L’heure affichée par le direct contre celle de ton téléphone. Plus de 5 secondes : pas de scalp aujourd’hui.'],
    ['Lis le sens', 'Sur ton graphique : le prix est-il au-dessus ou au-dessous de la VWAP ? C’est le seul sens autorisé.'],
    ['Pose la taille', 'Stop de ' + F.num(Math.max(4, Math.ceil(R.stopMinimal(set))), 0) + ' points au moins (plus bas, les coûts mangent le risque) : la taille se lit au desk Risque.']
  ].map(function (x) { return h('li', null, h('b', null, x[0]), h('span', null, x[1])); })));
  root.appendChild(s4);
  var s5 = U.section('Ce que la stratégie *doit battre*', 'calculé avec tes réglages');
  var rows = R.tableCouts(set, 2);
  s5.appendChild(U.table({ cols: [{ k: 'stop', label: 'Stop', fmt: function (v) { return v + ' pt'; } }, { k: 'risque', label: 'Risque', align: 'r', fmt: function (v) { return F.usd(v, 2); } }, { k: 'part', label: 'Coûts / risque', align: 'r', fmt: function (v) { return F.pct(v, 0); } }, { k: 'pm', label: 'Point mort à 1:2', align: 'r', fmt: function (v) { return F.pct(v, 1); } }], rows: rows, rowClass: function (r) { return r.part > 0.2 ? 'neg' : null; } }));
  s5.appendChild(U.prose([
    'Sans aucun avantage, un objectif à 2R avant un stop à 1R tombe <b>une fois sur trois</b> (33,3 %) : c’est la loi nulle, la même pour tout le monde. Pour gagner de l’argent, ta réussite doit dépasser le <b>point mort</b>, qui ajoute les coûts : ' + F.usd(R.cout(set), 2) + ' par aller-retour sur ' + set.instrument + ' (commission et un tick de glissement par jambe, déclaré).',
    'Sur un stop d’un point, les coûts pèsent ' + F.pct(rows[0].part, 0) + ' du risque et il faut gagner ' + F.pct(rows[0].pm, 0) + ' des trades. Sur un stop de quatre points, ' + F.pct(rows[3].part, 0) + ' et ' + F.pct(rows[3].pm, 0) + '. <b>Le scalp à stop minuscule perd sur les coûts, quelle que soit la lecture.</b> Lignes grisées : les coûts dépassent 20 % du risque.',
    'Distinguer une réussite cinq points au-dessus du point mort (à quatre points de stop) demande <b>' + F.int(R.tradesPourPreuve(rows[3].pm)) + ' trades</b>. Le testeur les compte.']));
  root.appendChild(s5);
}
function renderExemples(root, ctx) {
  var G = PF();
  var s1 = U.section('Douze *exemples*', 'trois gains, une perte, deux sorties, une sortie au temps, quatre refus, un non rempli');
  s1.appendChild(h('div', { class: 'rd-ex' }, G.SCALP_KEYS.map(exemple)));
  root.appendChild(s1);
  var s2 = U.section('Le mur, en *relief*', 'temps × prix × taille affichée');
  var P = T.lib.perf, box = h('div'), cas = T.store.get(K.view, 'tient');
  if (P && P.charts && P.charts.surface3d) {
    P.injectCss && P.injectCss();
    var paint = function () { T.clear(box); box.appendChild(U.chips({ options: [['tient', 'Tient'], ['recharge', 'Se recharge'], ['spawn', 'Apparu d’un coup'], ['retire', 'Retiré'], ['mange', 'Mangé'], ['espace', 'Deux murs']].map(function (o) { return { v: o[0], label: o[1] }; }), value: cas, onChange: function (v) { cas = v; T.store.set(K.view, v); paint(); } })); box.appendChild(P.charts.surface3d({ surf: G.surfScalp(cas) })); };
    paint();
    s2.appendChild(U.card({ title: 'Le carnet en relief', meta: 'schéma', body: [h('p', { class: 'note', style: 'margin:0' }, 'La crête est le mur. Il tient : elle court jusqu’au bout. Apparu d’un coup : elle surgit juste avant le contact puis tombe. Retiré : elle tombe d’un coup. Mangé : elle s’érode. Deux murs : deux crêtes parallèles, pas de place entre elles.'), box] }));
  }
  root.appendChild(s2);
}
function renderTester(root, ctx) {
  var set = ctx.settings, side = T.store.get(K.side, 'long'), st = R.stats(T.journal.list());
  var pm = R.pointMort(Math.max(4, Math.ceil(R.stopMinimal(set))), 2, set), need = R.tradesPourPreuve(pm);
  root.appendChild(h('div', { class: 'rd-hero' }, R.MOTS.map(function (x) { return x.m; }).join(' · ')));
  var s1 = U.section('Un geste par *trade*', 'en simulation d’abord');
  s1.appendChild(U.seg({ aria: 'Sens', value: side, onChange: function (v) { T.store.set(K.side, v); ctx.rerender(); }, options: [{ v: 'long', label: '▲ Achat' }, { v: 'short', label: '▼ Vente' }] }));
  var grid = h('div', { class: 'rd-log', style: 'margin-top:10px' });
  R.ISSUES.forEach(function (i) { grid.appendChild(U.button({ label: i.label, kind: i.tone || null, onClick: function () { var at = Date.now(); T.journal.add(R.entree(i.id, side, at, set.instrument)); T.toast(i.label + ' inscrit à ' + F.time(at)); } })); });
  var w = U.button({ label: 'Passé : une règle disait non', kind: 'ghost', onClick: function () { var at = Date.now(); T.journal.add(R.refus(at)); T.toast('Passe inscrite à ' + F.time(at)); } }); w.classList.add('wide'); grid.appendChild(w);
  s1.appendChild(grid);
  s1.appendChild(U.note('Chaque bouton inscrit un trade clos au journal (setup « Scalp Mur »), horodaté, avec son résultat en R. « Sortie mur » et « 3 min » portent un R estimé, à corriger au journal si tu veux le chiffre exact.'));
  root.appendChild(s1);
  var s2 = U.section('Où tu en *es*', st.n + ' trade' + (st.n > 1 ? 's' : ''));
  s2.appendChild(U.kpis([
    { label: 'Réussite', value: fin(st.wr) ? F.pct(st.wr, 1) : '—', hint: 'loi nulle 33,3 % · point mort ' + F.pct(pm, 1), tone: fin(st.wr) && st.wr > pm ? 'acc' : null },
    { label: 'R moyen', value: fin(st.moyR) ? F.r(st.moyR, 2) : '—', hint: 'avant coûts', tone: fin(st.moyR) && st.moyR < 0 ? 'neg' : null },
    { label: 'Total', value: F.r(st.totalR, 1), hint: st.passes + ' passe' + (st.passes > 1 ? 's' : '') },
    { label: 'Preuve', value: st.n + ' / ' + need, hint: 'trades pour séparer +5 points du point mort' }
  ], 4));
  if (st.eq.length > 1) s2.appendChild(T.chart.line({ series: [{ name: 'R cumulé', points: st.eq, tone: 'violet' }], x: { type: 'num', fmt: function (v) { return F.int(v); } }, y: { fmt: function (v) { return F.num(v, 1); }, zero: true }, height: 200 }));
  s2.appendChild(U.note(st.n < need ? 'Avant ' + need + ' trades, une réussite au-dessus du point mort peut venir du hasard seul : ne change pas les règles en route. L’effet à détecter est déclaré (cinq points), jamais tiré de ta réussite observée.' : 'Assez de trades pour juger un écart de cinq points au point mort. Compare ta réussite au point mort, pas à la loi nulle.'));
  root.appendChild(s2);
}
function renderEtudes(root) {
  var s = U.section('Ce que disent les *études*', 'liquidité affichée, sources vérifiées');
  s.appendChild(h('div', { class: 'rd-ex' }, R.ETUDES.map(function (e) {
    return U.card({ title: e.q, accent: e.v === 'établi', meta: R.VERDICTS[e.v], body: h('div', { class: 'rd-et' }, h('div', { class: 'pl-badge' + (e.v === 'établi' ? ' ok' : '') }, e.vt), h('ul', null, e.p.map(function (x) { return h('li', null, x); })), h('p', { class: 'pl-vf' }, h('span', { class: 'pl-tag' }, 'Pour toi'), e.implication), h('div', { class: 'rd-src' }, e.src.map(function (x) { return h('a', { href: x[1], target: '_blank', rel: 'noopener' }, x[0]); }))) });
  })));
  s.appendChild(U.note('Résumés à partir des résumés publiés et des communiqués officiels. Aucune de ces études ne mesure la rentabilité d’un scalp sur la heatmap : c’est au testeur de le faire.'));
  root.appendChild(s);
}

var TABS = [{ id: 'carte', label: 'Scalp Mur' }, { id: 'exemples', label: 'Exemples' }, { id: 'tester', label: 'Tester' }, { id: 'etudes', label: 'Études' }];
T.desk({
  id: 'rnd', label: 'Recherche & dév', glyph: '◇', group: 'Recherche', order: 44, tabs: TABS,
  render: function (root, ctx) {
    injectCss(); if (T.lib.plan && T.lib.plan.injectCss) T.lib.plan.injectCss();
    var tab = TABS.some(function (t) { return t.id === ctx.tab; }) ? ctx.tab : 'carte';
    var heads = { carte: ['R&D · Scalp Mur', 'Six mots, *par cœur*.', 'Un scalp de quelques secondes à trois minutes, sur un mur de liquidité du bon côté de la VWAP, objectif 2R. Pensé pour un téléphone et le direct YouTube de Bookmap.'], exemples: ['R&D · Exemples', 'Douze cas, *calculés*.', 'Chaque planche applique les six règles au chemin dessiné ; le résultat n’est jamais écrit à la main.'], tester: ['R&D · Tester', 'Le compter, *pas le croire*.', 'Un bouton par trade, en simulation d’abord. La réussite se compare au point mort, avec le nombre de trades qu’il faut pour conclure.'], etudes: ['R&D · Études', 'Ce que la liquidité *prouve*.', 'Les affirmations courantes sur les murs, confrontées aux études et aux dossiers de régulation.'] }[tab];
    root.appendChild(U.page({ kicker: heads[0], title: heads[1], lede: heads[2] }));
    root.appendChild(U.tabs({ tabs: TABS, value: tab, onChange: ctx.setTab }));
    if (tab === 'exemples') renderExemples(root, ctx);
    else if (tab === 'tester') renderTester(root, ctx);
    else if (tab === 'etudes') renderEtudes(root);
    else renderCarte(root, ctx);
    var un = T.journal.on(function () { if (tab === 'tester') ctx.rerender(); });
    return function () { un(); };
  }
});
