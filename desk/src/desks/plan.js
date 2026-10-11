/* Desk « Plan de trading » : la carte de la journée, de la macro au trade, avec un pourcentage par étape ;
   chaque étape dit quoi préparer, montre ses situations en schémas (2D) et en relief (3D), et se valide d’un bouton
   qui ramène à la carte. Le mode Live tient sur un écran : où j’en suis, les zones du jour, six cases, deux boutons.
   Le journal se complète après la séance : un trade pris en live s’inscrit d’un geste, horodaté, statut « ouvert ».
   Sources : ALP nº 3, partie III (catalogue, grammaire du setup : la confirmation ne déplace pas l’espérance),
   partie XIX (largeur d’un niveau, le nœud de faible volume), partie XXX (trois fins d’une position, portée de séance).
   Les schémas sont des illustrations, jamais des données de marché ; les reliefs sont calculés. */
var h = T.h, U = T.ui, F = T.fmt;
T.lib = T.lib || {};
var L = T.lib.plan = {};
var K = { day: 'plan:day', open: 'plan:open', prefs: 'plan:prefs', view: 'plan:vue', nqBias: 'nq:bias', nqGex: 'nq:gex' };
L.KEYS = K;
function fin(v) { return typeof v === 'number' && isFinite(v); }
function pad2(n) { return String(n).padStart(2, '0'); }
function clone(o) { return JSON.parse(JSON.stringify(o)); }

/* =====================================================================
   1. Fonctions pures — aucun DOM
   ===================================================================== */

/* Choix durables de la méthode (ils ne changent pas chaque jour). Déclarés, modifiables, jamais tirés des résultats. */
L.PREFS0 = { trig: null, avant: 5, apres: 15, rrMin: 3, marge: 4, range: null, tick: 0.25 };
L.normPrefs = function (raw) {
  var p = Object.assign({}, L.PREFS0, raw && typeof raw === 'object' ? raw : {});
  if (['absorption', 'epuisement', 'continuation'].indexOf(p.trig) < 0) p.trig = null;
  ['avant', 'apres', 'rrMin', 'marge', 'tick'].forEach(function (k) { if (!fin(p[k]) || p[k] < 0) p[k] = L.PREFS0[k]; });
  if (!(fin(p.range) && p.range > 0)) p.range = null;
  return p;
};

/* Les étapes de la carte, dans l’ordre du plan. Les identifiants sont ceux de T.DAY_STEPS.
   Chaque étape est un déroulé : chaque moment dit quoi VOIR (ses figures, 2D et 3D, à faire glisser) puis quoi FAIRE
   (un champ, un réglage), et se coche. Figures : s (schéma), v (VWAP calculée), fp (footprint chiffré),
   liq (carte de liquidité et son footprint), vp, day (frise), carte (le setup sur tes niveaux), relief, ladder. */
L.STEPS = [
  { id: 'macro', t: 'Macro et calendrier', short: 'Macro',
    k5: 'Avant de jouer dehors, on regarde la météo. Si un orage est annoncé à 14 h 30, on ne sort pas à 14 h 25.',
    items: [
      { t: 'Annonces de rang 1 relevées', voir: 'Le calendrier du jour : seulement les annonces à trois pastilles, à l’heure de Paris.', faire: 'Recopie-les en une ligne. La frise calcule tes fenêtres interdites à mesure que tu écris.', input: 'annonces', desk: 'macro', tab: 'calendrier', go: 'Calendrier', figs: [{ day: 1 }, { s: 'macroPublic' }] },
      { t: 'Déjà dans le prix ?', voir: 'Le NQ a-t-il couru vers l’annonce les jours d’avant ? Une rumeur se lit comme une pente, pas comme un saut.', faire: 'Si la rumeur est jouée, une nouvelle conforme n’est pas un signal dans son sens : ceux qui ont acheté la rumeur vendent l’annonce.', principe: true, figs: [{ s: 'macroRumeur' }, { s: 'macroPrix' }, { s: 'macroPrive' }] },
      { t: 'Fenêtres interdites posées', voir: 'La frise du jour : en violet, les minutes sans ordre. À l’ouverture américaine, le prix touche les bandes pour de mauvaises raisons.', faire: 'Règle les minutes avant et après. Le mode Live les lit à l’horloge et bloque la première case.', input: 'fenetres', figs: [{ day: 1 }, { v: 'ouverture' }] }] },
  { id: 'biais', t: 'Tendance : haussière, neutre ou baissière', short: 'Tendance',
    k5: 'On regarde dans quel sens coule la rivière. On nage avec elle. Si elle change de sens pendant la journée, on sort de l’eau.',
    items: [
      { t: 'Tendance de la veille', voir: 'La séance d’hier : sommets et creux montants (haussière), descendants (baissière), ou à plat (neutre).', faire: 'Choisis la forme qui ressemble à hier. La planche choisie passe en premier.', input: 'veille', figs: [{ s: 'dowHausse', sel: 'hausse' }, { s: 'dowRange', sel: 'range' }, { s: 'dowBaisse', sel: 'baisse' }] },
      { t: 'Structure de Dow aujourd’hui', voir: 'Depuis l’ouverture : la structure suit-elle la veille, ou le dernier creux (ou sommet) a-t-il cédé ?', faire: 'Alignée : la tendance tient. Cassée : neutre, pas de trade dans l’ancien sens.', input: 'dow', figs: [{ s: 'dowCassure', sel: 'casse' }, { s: 'dowHausse', sel: 'aligne' }] },
      { t: 'Tendance déclarée', voir: 'La tendance qui sort des deux réponses, et le sens qu’elle autorise.', faire: 'Note le niveau qui l’annulerait. La tendance ne se rediscute plus avant demain, sauf cassure.', input: 'biais', figs: [{ v: 'achat', bias: 'long' }, { v: 'vente', bias: 'short' }, { v: 'neutre', bias: 'both' }] }] },
  { id: 'gex', t: 'Tracer les niveaux gamma', short: 'Gamma',
    k5: 'On pose les drapeaux d’arrivée avant la course : ce sont tes cibles.',
    items: [
      { t: 'Export GEX collé', voir: 'L’export du robot, vers 6 h, collé tel quel dans NQ › GEX.', faire: 'Colle-le là-bas : le desk le lit et le porte sur le NQ. Il revient ici tout seul. Sinon, note les niveaux à la main.', input: 'gex', desk: 'nq', tab: 'gex', go: 'Coller le GEX', figs: [{ s: 'gexZone' }] },
      { t: 'Niveaux sur l’échelle du NQ', voir: 'Si le robot publie des strikes NDX, la base NQ − NDX doit être appliquée.', faire: 'Vérifie que les niveaux tombent près du prix du NQ, pas à des centaines de points.', figs: [{ ladder: 1 }] },
      { t: 'Niveaux tracés sur ton graphique', voir: 'Chaque niveau est une zone, pas un trait : sa demi-largeur vaut 1,177 σ√T (ALP nº 3, partie XIX).', faire: 'Trace-les. Ils serviront de cibles, jamais d’entrées.', figs: [{ s: 'gexPortee' }, { s: 'gexLoin' }] }] },
  { id: 'zones', t: 'Tracer les HVN', short: 'HVN',
    k5: 'On trace les endroits où tout le monde s’est retrouvé hier : les places pleines. Le prix ralentit dessus.',
    items: [
      { t: 'Profil d’hier tracé', voir: 'Le profil de volume posé sur la structure d’hier : ses bosses sont les HVN, les nœuds de haut volume.', faire: 'Trace-le du dernier sommet au dernier creux qui comptent, ou sur la séance entière.', figs: [{ vp: 1 }, { relief: 'profil' }] },
      { t: 'HVN notés', voir: 'Chaque bosse du profil, en fourchette : le prix la traverse, y rebondit après l’avoir traversée, ou n’y vient pas.', faire: 'Note un bas et un haut par HVN (« 31080-31095 »), jamais un trait. Seulement les HVN.', input: 'hvn', figs: [{ s: 'zoneRebond' }, { s: 'zoneTraverse' }, { s: 'zoneIgnore' }] },
      { t: 'HVN enregistrés', voir: 'Tes niveaux du jour, HVN et gamma ensemble.', faire: 'Enregistre-les pour le Labo : chaque matin compte pour tester la méthode plus tard.', input: 'labo', figs: [{ ladder: 1 }] }] },
  { id: 'setup', t: 'Ta carte : y a-t-il un setup ?', short: 'Setup',
    k5: 'On regarde la carte avant de partir : d’où on part, où on s’arrête si ça tourne mal, où on veut arriver.',
    items: [
      { t: 'Prix et séance notés', voir: 'Le prix du moment, et la distance qu’une séance parcourt d’habitude sur ton graphique.', faire: 'Saisis-les : la carte et la portée de chaque cible en dépendent.', input: 'prix', figs: [] },
      { t: 'La carte du jour lue', voir: 'Ta tendance, tes HVN et tes niveaux gamma sur une seule planche, avec le meilleur setup tracé : entrée au bord du HVN, stop derrière, cible gamma.', faire: 'Si la carte ne trace rien, il n’y a pas de setup aujourd’hui à ce prix.', figs: [{ carte: 1 }] },
      { t: 'Setups candidats', voir: 'Chaque HVN du bon côté du prix, avec chaque niveau gamma en face : R:R et portée calculés.', faire: 'Garde ceux qui passent ton R:R minimal et restent dans la portée de la séance. Les autres n’existent pas.', input: 'setups', figs: [] }] },
  { id: 'fenetre', t: 'VWAP : contact de ±1,5σ ou ±2,5σ', short: 'VWAP',
    k5: 'La VWAP est le prix moyen de la journée. On achète en solde, sous la bande ; on vend trop cher, au-dessus.',
    items: [
      { t: 'VWAP et bandes affichées', voir: 'Comme sur ton graphique : la VWAP en blanc, ancrée à minuit, et ses bandes à ±1,5σ et ±2,5σ.', faire: 'Affiche les deux bandes. Un contact de l’une ou de l’autre compte.', figs: [{ v: 'neutre' }, { v: 'ouverture' }] },
      { t: 'Le bon côté touché', voir: 'Tendance haussière : contact de −1,5σ ou −2,5σ. Tendance baissière : contact de +1,5σ ou +2,5σ.', faire: 'Pas de contact de bande du bon côté, pas de trade.', input: 'sens', figs: [{ v: 'achat', bias: 'long' }, { v: 'vente', bias: 'short' }] },
      { t: 'Côté interdit compris', voir: 'Le prix reste du mauvais côté, ou tourne autour de la VWAP sans toucher une bande.', faire: 'On attend, on ne force pas.', figs: [{ v: 'attendre' }, { v: 'neutre' }] }] },
  { id: 'declencheur', t: 'Absorption, épuisement ou continuation', short: 'Flux',
    k5: 'Au contact, on regarde qui gagne : celui qui pousse ou celui qui tient. Si personne ne tient, on suit celui qui pousse.',
    items: [
      { t: 'Ce que fait la zone au contact', voir: 'Le footprint au contact : absorption (beaucoup de volume, le prix ne passe pas), épuisement (plus rien ne s’échange), ou cassure (la zone cède).', faire: 'Absorption ou épuisement : retournement dans le sens de la tendance. La zone cède dans le sens de la tendance : continuation.', input: 'trig', figs: [{ fp: 'absorptionAcheteuse' }, { fp: 'absorptionVendeuse' }, { fp: 'epuisement' }, { fp: 'mangee' }] },
      { t: 'Les issues possibles', voir: 'La carte du carnet et le footprint, cas par cas : la zone tient, se recharge, s’épuise, cède (continuation), est retirée, ou n’est jamais touchée.', faire: 'Badge violet : un trade existe. Badge gris : aucun.', figs: [{ liq: 'tient' }, { liq: 'resistance' }, { liq: 'recharge' }, { liq: 'epuisement' }, { liq: 'continuation' }, { liq: 'mangee' }, { liq: 'retiree' }, { liq: 'ignoree' }] },
      { t: 'Continuation : la zone ne tient pas', voir: 'Des déséquilibres empilés du côté de la tendance cassent la zone ; l’ancien support devient résistance.', faire: 'Entrée au retour sous (ou sur) l’ancienne zone, dans le sens de la tendance seulement.', figs: [{ liq: 'continuation' }, { fp: 'initiative' }] },
      { t: 'Invalidation relue', voir: 'L’absorption a eu lieu, puis une clôture traverse la zone de plus d’un écart-type dans les 15 minutes.', faire: 'Sortie immédiate. Le signal n’était pas une promesse.', figs: [{ fp: 'invalidation' }] }] },
  { id: 'mur', t: 'Le mur de liquidité et le stop', short: 'Mur',
    k5: 'On met le filet derrière le gros rocher, pas devant : si le rocher tient, on est à l’abri.',
    items: [
      { t: 'Un mur réel à la zone', voir: 'Sur la heatmap, une ligne de liquidité nette à la zone, qui échange au contact (bulles) sans fondre.', faire: 'Pas de mur, pas de stop protégé : pas de trade.', figs: [{ liq: 'tient' }, { liq: 'recharge' }, { relief: 'liq' }] },
      { t: 'Un mur ancien, pas apparu d’un coup', voir: 'Un mur qui surgit au dernier moment et disparaît au contact est la forme exacte des ordres de manipulation sanctionnés sur le CME.', faire: 'Ne compte que les murs présents depuis plusieurs minutes. Voir R&D › Études.', figs: [{ liq: 'spawn' }, { liq: 'retiree' }] },
      { t: 'Stop derrière le mur', voir: 'Tendance haussière : stop sous le mur. Tendance baissière : stop au-dessus. Jamais devant.', faire: 'Saisis la distance du stop : le prix au-delà du mur, plus ta marge.', input: 'stop', figs: [{ s: 'risqueStop' }, { s: 'risqueBruit' }] },
      { t: 'Le mur a été touché', voir: 'Le prix est venu sur le mur et des bulles s’y sont imprimées : il a échangé et tenu.', faire: 'Sans contact, l’ordre ne part pas.', figs: [{ liq: 'tient' }, { liq: 'ignoree' }] }] },
  { id: 'risque', t: 'Cible gamma et grand R:R', short: 'Cible',
    k5: 'On vise loin avec un petit filet. On gagne rarement, mais gros. Il faut savoir combien de fois on perdra avant.',
    items: [
      { t: 'Stop hors du bruit', voir: 'Le bruit d’une minute se calcule à partir de la distance qu’une séance parcourt. Un stop plus petit que lui est pris par le hasard.', faire: 'Garde un stop d’au moins trois fois ce bruit, choix déclaré.', input: 'bruit', figs: [] },
      { t: 'Cible = niveau gamma', voir: 'La cible est le niveau gamma en face, posé juste avant sa zone.', faire: 'Lis le R:R sur la carte du jour.', figs: [{ carte: 1 }] },
      { t: 'Ce que coûte un R:R de 1:30 à 1:500', voir: 'Plus le R:R est grand, plus la cible est rare : la probabilité de l’atteindre, le nombre de trades pour voir un gain, la portée de la séance.', faire: 'Choisis un R:R que la séance peut porter, et accepte les séries de pertes qu’il implique.', input: 'grandrr', figs: [{ relief: 'gros' }, { relief: 'fins' }] },
      { t: 'Taille et limites', voir: 'Risque par trade ÷ (stop × valeur du point + commission), et les limites du jour.', faire: 'Une limite atteinte, la journée est finie.', input: 'taille', desk: 'risk', go: 'Risque', figs: [] }] },
  { id: 'journal', t: 'Journal, après', short: 'Journal',
    k5: 'Pendant le match on joue, on ne prend pas de notes. Après le match, on écrit ce qui s’est passé, même les fois où on n’a pas tiré.',
    items: [
      { t: 'Trades du jour complétés', voir: 'Les trades pris en live sont au journal, horodatés, statut « ouvert ».', faire: 'Complète entrée, stop, sortie et résultat.', desk: 'journal', tab: 'registre', go: 'Registre', figs: [] },
      { t: 'Plan respecté, oui ou non', voir: 'Une case par trade.', faire: 'Sans commentaire : oui ou non.', figs: [] }] },
  { id: 'revue', t: 'Revue du soir', short: 'Revue',
    k5: 'Le soir, on regarde ce qu’on a fait, pas ce que le marché a fait.',
    items: [
      { t: 'Revue faite', voir: 'La routine du soir : trois questions, cinq minutes.', faire: 'Réponds dans le desk Routine.', desk: 'routine', go: 'Routine', figs: [] },
      { t: 'Une seule chose à changer', voir: 'Ce que la journée enseigne sur ton exécution, pas sur le marché.', faire: 'Une chose, ou rien : un plan ne se réécrit pas après une seule journée.', figs: [] }] }
];
L.STEP = {}; L.STEPS.forEach(function (s, i) { s.n = i + 1; L.STEP[s.id] = s; });
L.PREP = ['macro', 'biais', 'gex', 'zones', 'setup', 'fenetre', 'declencheur', 'mur', 'risque'];

/* État du jour : il repart à zéro chaque jour (heure de Paris). */
L.normDay = function (raw, today) {
  var s = raw && typeof raw === 'object' && raw.date === today ? raw : {};
  var ch = s.checks && typeof s.checks === 'object' ? s.checks : {}, checks = {};
  L.STEPS.forEach(function (st) { var a = Array.isArray(ch[st.id]) ? ch[st.id] : []; checks[st.id] = st.items.map(function (_, i) { return !!a[i]; }); });
  var str = function (v) { return typeof v === 'string' ? v : ''; };
  var live = s.live && typeof s.live === 'object' ? s.live : {};
  return {
    date: today, checks: checks,
    annonces: str(s.annonces), regime: ['on', 'off', 'neutre'].indexOf(s.regime) >= 0 ? s.regime : null,
    veille: ['hausse', 'baisse', 'range'].indexOf(s.veille) >= 0 ? s.veille : null,
    dow: ['aligne', 'casse', 'flou'].indexOf(s.dow) >= 0 ? s.dow : null,
    invalid: str(s.invalid), hvn: str(s.hvn != null ? s.hvn : s.hvz), gexMan: str(s.gexMan),
    stop: fin(s.stop) && s.stop > 0 ? s.stop : null, prix: fin(s.prix) && s.prix > 0 ? s.prix : null,
    live: { zone: !!live.zone, vwap: !!live.vwap, signal: !!live.signal, mur: !!live.mur, risque: !!live.risque, etat: L.ETATS_IDS.indexOf(live.etat) >= 0 ? live.etat : null }
  };
};
L.ownPct = function (day, id) { var c = day.checks[id] || []; return c.length ? Math.round(100 * c.filter(Boolean).length / c.length) : 0; };
L.toggle = function (day, id, i) { var d = clone(day); if (d.checks[id] && i >= 0 && i < d.checks[id].length) d.checks[id][i] = !d.checks[id][i]; return d; };
/* Avancement de la préparation : moyenne des neuf étapes d’avant le trade. pctOf(id) lit T.day.pct. */
L.prepPct = function (pctOf) { var s = 0; L.PREP.forEach(function (id) { s += pctOf(id); }); return Math.round(s / L.PREP.length); };

/* Niveaux saisis à la main. Séparateurs : point-virgule, retour à la ligne, virgule suivie d’une espace, « / ».
   Dans un élément : deux nombres forment une fourchette, un seul un prix ; la virgule collée est décimale (21480,25). */
L.parseLevels = function (text, prefix) {
  var out = [];
  String(text == null ? '' : text).split(/[;\n]+|,\s+|\s+\/\s+/).forEach(function (tok) {
    var t = tok.trim(); if (!t) return;
    var nums = (t.match(/\d+(?:[.,]\d+)?/g) || []).map(function (x) { return parseFloat(x.replace(',', '.')); }).filter(function (v) { return v > 0; });
    if (!nums.length) return;
    var lo = Math.min(nums[0], nums.length > 1 ? nums[1] : nums[0]), hi = Math.max(nums[0], nums.length > 1 ? nums[1] : nums[0]);
    var label = t.replace(/\d+(?:[.,]\d+)?/g, '').replace(/[-–—:=]+/g, ' ').replace(/\s+/g, ' ').trim();
    out.push({ lo: lo, hi: hi, mid: (lo + hi) / 2, label: label || (prefix || 'Niveau') + ' ' + (out.length + 1) });
  });
  return out;
};
/* Annonces : « 14:30 CPI, 16h ISM, 20 h FOMC » → minutes depuis minuit (heure de Paris) et libellé. */
L.parseTimes = function (text) {
  var out = [];
  String(text == null ? '' : text).split(/[;\n]+|,\s*|\s+\/\s+/).forEach(function (tok) {
    var t = tok.trim(), m = t.match(/(\d{1,2})\s*(?:[:hH.]\s*(\d{2})?)/); if (!m) return;
    var hh = +m[1], mm = m[2] ? +m[2] : 0; if (hh > 23 || mm > 59) return;
    var label = t.replace(m[0], '').replace(/\s+/g, ' ').trim();
    out.push({ min: hh * 60 + mm, hhmm: pad2(hh) + ':' + pad2(mm), label: label || 'annonce' });
  });
  return out.sort(function (a, b) { return a.min - b.min; });
};
/* Fenêtre interdite : de « avant » minutes avant à « apres » minutes après chaque annonce. */
L.forbidden = function (nowMin, events, avant, apres) {
  var cur = null, next = null;
  (events || []).forEach(function (e) {
    var a = e.min - avant, b = e.min + apres;
    if (nowMin >= a && nowMin < b) { if (!cur || b > cur.until) cur = { ev: e, from: a, until: b }; }
    else if (a > nowMin && (!next || a < next.from)) next = { ev: e, from: a, until: b };
  });
  return { now: cur, next: next };
};
L.minText = function (m) { m = ((Math.round(m) % 1440) + 1440) % 1440; return pad2(Math.floor(m / 60)) + ':' + pad2(m % 60); };

/* Biais : la veille donne le sens, la structure de Dow peut le suspendre. Le range ne donne aucun sens. */
L.biasOf = function (veille, dow) {
  if (!veille) return null;
  if (veille === 'range' || dow === 'casse') return 'both';
  return veille === 'hausse' ? 'long' : 'short';
};
L.biasWord = function (b) { return b === 'long' ? 'acheteur' : b === 'short' ? 'vendeur' : b === 'both' ? 'neutre' : null; };
L.sideRule = function (bias) {
  if (bias === 'long') return { short: 'Achats à −1,5σ ou −2,5σ', long: 'Tendance haussière : achats seulement au contact de la bande −1,5σ ou −2,5σ de la VWAP. Aucune vente aujourd’hui.' };
  if (bias === 'short') return { short: 'Ventes à +1,5σ ou +2,5σ', long: 'Tendance baissière : ventes seulement au contact de la bande +1,5σ ou +2,5σ de la VWAP. Aucun achat aujourd’hui.' };
  if (bias === 'both') return { short: 'Neutre : pas de sens', long: 'Tendance neutre ou structure cassée : pas de trade, même au contact d’une bande.' };
  return { short: 'Tendance à déclarer', long: 'Déclare la tendance à l’étape 2 : le sens autorisé en découle.' };
};
L.allowed = function (bias, side) { return bias === 'long' ? side === 'long' : bias === 'short' ? side === 'short' : false; };

/* Taille : contrats entiers dont la perte au stop, commission comprise, tient dans le risque par trade. */
L.contracts = function (risk, stopPts, pointValue, commissionRT) {
  if (!(risk > 0) || !(stopPts > 0) || !(pointValue > 0)) return 0;
  var per = stopPts * pointValue + (fin(commissionRT) ? commissionRT : 0);
  return Math.max(0, Math.floor(risk / per + 1e-9));
};

/* Le mode Live : six cases, dans l’ordre du plan. La première n’est pas une case : elle se lit à l’horloge. */
L.ETATS_IDS = ['tient', 'recharge', 'epuisement', 'continuation', 'retiree', 'mangee', 'spawn'];
L.LIVE = [
  { id: 'fenetre', t: 'Hors fenêtre interdite', stage: 'macro', auto: true },
  { id: 'zone', t: 'Au contact d’un HVN', s: 'Un HVN noté ce matin, du bon côté du prix', stage: 'declencheur' },
  { id: 'vwap', t: 'Bande VWAP touchée du bon côté', s: '', stage: 'vwap' },
  { id: 'signal', t: 'Absorption, épuisement ou continuation', s: 'Le flux dit qui gagne au contact', stage: 'declencheur' },
  { id: 'mur', t: 'Un mur ancien, stop derrière lui', s: 'Présent depuis plusieurs minutes, touché, il tient', stage: 'declencheur' },
  { id: 'risque', t: 'Cible gamma, R:R tenu', s: '', stage: 'risque' }
];
L.liveState = function (day, fenetreOk) {
  var miss = null;
  L.LIVE.forEach(function (c) { var ok = c.auto ? fenetreOk : !!day.live[c.id]; if (!ok && !miss) miss = c; });
  return { ok: !miss, miss: miss, n: L.LIVE.filter(function (c) { return c.auto ? fenetreOk : !!day.live[c.id]; }).length };
};
L.resetLive = function (day) { var d = clone(day); d.live = { zone: false, vwap: false, signal: false, mur: false, risque: false, etat: null }; return d; };
L.TRIG = { absorption: 'Absorption', epuisement: 'Épuisement', continuation: 'Continuation' };
L.setupText = function (prefs, etat) { var e = etat === 'continuation' ? 'Continuation' : etat === 'epuisement' ? 'Épuisement' : etat === 'tient' || etat === 'recharge' ? 'Absorption' : null; return 'Plan HVN · ' + (e || 'flux non noté'); };
L.prisEntry = function (side, prefs, ok, at, instrument, etat) { return { kind: 'pris', side: side, setup: L.setupText(prefs, etat), status: 'ouvert', plan: !!ok, at: at, instrument: instrument, note: 'Inscrit en live depuis le plan : à compléter.' }; };
/* Un refus ne porte ni sens ni mise (contrat du journal). */
L.refusEntry = function (miss, prefs, at, etat) { return { kind: 'refus', stage: miss ? miss.stage : 'autre', setup: L.setupText(prefs, etat), at: at }; };

/* Le jour du journal, en heure de Paris. */
L.dayKeyOf = function (ms) { var p = T.time.parts('Europe/Paris', new Date(ms)); return p.y + '-' + pad2(p.mo) + '-' + pad2(p.d); };
L.todayStats = function (rows, today) {
  var r = (rows || []).filter(function (x) { return x && fin(x.at) && L.dayKeyOf(x.at) === today; }), taken = r.filter(function (x) { return x.kind === 'pris'; });
  var pnl = taken.reduce(function (a, x) { return a + (fin(x.pnl) ? x.pnl : 0); }, 0);
  return { n: r.length, taken: taken.length, losses: taken.filter(function (x) { return x.pnl < 0; }).length, pnl: pnl, open: taken.filter(function (x) { return x.status === 'ouvert' || (!fin(x.pnl) && !fin(x.exit)); }).length };
};

/* Les HVN du jour pour le Labo : noms HVN1, HVN2…, au milieu de chaque fourchette. */
L.labLevels = function (day) {
  var o = {};
  L.parseLevels(day.hvn, 'HVN').forEach(function (z, i) { o['HVN' + (i + 1)] = z.mid; });
  return o;
};

/* La carte : chaque HVN du bon côté du prix, face à chaque niveau gamma. Entrée au bord du HVN côté prix, stop au-delà
   du HVN plus la marge, cible le niveau gamma. Rien n’est retenu si la tendance ne donne pas de sens. o.range, la
   distance qu’une séance parcourt d’habitude (saisie), donne la portée ; σ de séance = range / 1,596 (étendue
   moyenne d’un mouvement brownien : 2√(2/π) σ). */
L.RANGE_TO_SIGMA = 2 * Math.sqrt(2 / Math.PI);
L.setups = function (o) {
  var out = [], side = o.bias === 'long' ? 1 : o.bias === 'short' ? -1 : 0, m = (o.marge || 0) * (o.tick || 0.25);
  if (!side || !fin(o.price)) return out;
  var sig = fin(o.range) && o.range > 0 ? o.range / L.RANGE_TO_SIGMA : null;
  (o.hvn || []).forEach(function (z) {
    if (side > 0 ? z.hi > o.price : z.lo < o.price) return;
    var entry = side > 0 ? z.hi : z.lo, stop = side > 0 ? z.lo - m : z.hi + m, risk = Math.abs(entry - stop);
    if (!(risk > 0)) return;
    (o.gamma || []).forEach(function (g) {
      if (side > 0 ? g.price <= entry : g.price >= entry) return;
      var dist = Math.abs(g.price - entry), rr = dist / risk, p = sig ? L.issues(risk / sig, dist / sig) : null;
      out.push({ side: side, zone: z, entry: entry, stop: stop, target: g.price, label: g.label, risk: risk, dist: dist, rr: rr, portee: sig ? dist <= o.range : null, pObjectif: p ? p.objectif : null, pCloche: p ? p.cloche : null });
    });
  });
  out.sort(function (a, b) { return (b.rr >= (o.rrMin || 0)) - (a.rr >= (o.rrMin || 0)) || (b.portee !== false) - (a.portee !== false) || Math.abs(a.entry - o.price) - Math.abs(b.entry - o.price) || b.rr - a.rr; });
  return out;
};
L.best = function (list, rrMin) { return list.filter(function (x) { return x.rr >= rrMin && x.portee !== false; })[0] || null; };
/* Le bruit d’une minute : σ de séance / √1 380 (la séance Globex en minutes). */
L.bruitMinute = function (range) { return fin(range) && range > 0 ? range / L.RANGE_TO_SIGMA / Math.sqrt(1380) : null; };
/* Ce que coûte un grand R:R : sans dérive, à la portée de la séance, avec les coûts. */
L.GRANDS_RR = [2, 5, 10, 30, 100, 500];
L.grandRR = function (stop, range, costUsd, pointValue) {
  var sig = fin(range) && range > 0 ? range / L.RANGE_TO_SIGMA : null, c = stop > 0 && pointValue > 0 ? costUsd / (stop * pointValue) : 0;
  return L.GRANDS_RR.map(function (rr) {
    var target = rr * stop, pLibre = 1 / (1 + rr), p = sig && stop > 0 ? L.issues(stop / sig, target / sig).objectif : null;
    var n90 = p > 0 && p < 1 ? Math.log(0.1) / Math.log(1 - p) : p === 0 ? Infinity : null;
    return { rr: rr, target: target, pLibre: pLibre, pSeance: p, equilibre: (1 + c) / (1 + rr), n90: n90, portee: range > 0 ? target / range : null, serie: p > 0 ? Math.log(100 * p) / -Math.log(1 - p) : null };
  });
};

/* ---------- Reliefs calculés (aucune donnée de marché) ---------- */
/* Arrêt à deux barrières sans dérive, horizon fini : probabilité de toucher l’objectif (à b) avant le stop (à a)
   pendant une séance, a et b en écarts-types de séance. Série exacte du mouvement brownien (cf. microSeuil, µ = 0) :
   P = a/(a+b) − Σ (−1)^{n+1} (2/nπ) sin(nπa/l) e^{−(nπ/l)²/2}. La part restante se partage entre stop et cloche. */
L.issues = function (a, b) {
  var l = a + b, al = Math.PI * a / l, up = 0, down = 0, quiet = 0;
  for (var n = 1; n <= 4000; n++) {
    var lam = Math.pow(n * Math.PI / l, 2) / 2, base = (2 / (n * Math.PI)) * Math.sin(n * al) * Math.exp(-lam);
    down += base; up += (n % 2) ? base : -base;
    if (Math.abs(base) < 1e-13) { if (++quiet > 12) break; } else quiet = 0;
  }
  var pT = Math.min(1, Math.max(0, a / l - up)), pS = Math.min(1, Math.max(0, b / l - down));
  return { objectif: pT, stop: pS, cloche: Math.max(0, 1 - pT - pS) };
};
function lin(a, b, n) { var o = []; for (var i = 0; i < n; i++) o.push(a + i * (b - a) / (n - 1)); return o; }
function surf(def, xs, ys) {
  var vals = ys.map(function (y) { return xs.map(function (x) { return def.fn(x, y); }); }), lo = Infinity, hi = -Infinity, am = [0, 0];
  vals.forEach(function (row, j) { row.forEach(function (v, i) { if (!fin(v)) return; if (v < lo) lo = v; if (v > hi) { hi = v; am = [i, j]; } }); });
  return Object.assign(def, { xs: xs, ys: ys, vals: vals, zmin: lo, zmax: hi, argmax: am });
}
L.surfFins = function (n) {
  n = n || 24;
  return surf({ title: 'Objectif touché dans la séance', x: { name: 'stop', dom: [0.1, 1], fmt: function (v) { return F.num(v, 2) + ' σ'; } }, y: { name: 'R:R', dom: [0.5, 4], fmt: function (v) { return F.num(v, 1); } },
    z: { name: 'objectif avant stop et cloche', fmt: function (v) { return F.pct(v, 1); } }, fn: function (a, rr) { return L.issues(a, a * rr).objectif; }, mid: null }, lin(0.1, 1, n), lin(0.5, 4, n));
};
/* Délai pour réunir 619 décisions (ALP nº 3, table 14) : contacts par semaine × part gardée par la confirmation. Hauteur en log10(années). */
L.N_PREUVE = 619;
L.surfDelai = function (n) {
  n = n || 24;
  var yrs = function (v) { var y = Math.pow(10, v); return y < 1 ? F.num(y * 12, 1) + ' mois' : F.num(y, y < 10 ? 1 : 0) + ' ans'; };
  return surf({ title: 'Délai pour 619 décisions', x: { name: 'part gardée', dom: [0.02, 1], fmt: function (v) { return F.pct(v, 0); } }, y: { name: 'contacts par semaine', dom: [2, 30], fmt: function (v) { return F.num(v, 0); } },
    z: { name: 'délai', fmt: yrs }, fn: function (f, c) { return Math.log10(L.N_PREUVE / (c * f) / 52); }, mid: null }, lin(0.02, 1, n), lin(2, 30, n));
};
/* Le nombre de trades pour voir au moins un gain, à 90 % : R:R (échelle log) × stop en σ de séance. Hauteur en log10. */
L.surfGros = function (n) {
  n = n || 22;
  var fmtN = function (v) { var x = Math.pow(10, v); return x >= 1e5 - 1 ? '≥ 100 000' : F.int(Math.ceil(x)); };
  return surf({ title: 'Trades pour voir un gain', x: { name: 'R:R', dom: [Math.log10(2), Math.log10(500)], fmt: function (v) { return '1:' + F.num(Math.pow(10, v), Math.pow(10, v) < 10 ? 1 : 0); } }, y: { name: 'stop', dom: [0.02, 0.4], fmt: function (v) { return F.num(v, 2) + ' σ de séance'; } },
    z: { name: 'trades pour un gain à 90 %', fmt: fmtN }, fn: function (lx, a) { var p = L.issues(a, a * Math.pow(10, lx)).objectif; return p > 1e-6 ? Math.min(5, Math.log10(Math.log(0.1) / Math.log(1 - p))) : 5; }, mid: null }, lin(Math.log10(2), Math.log10(500), n), lin(0.02, 0.4, n));
};
/* Profil de volume qui se construit pendant une séance : schéma (deux nœuds, un creux entre eux), pas une donnée. */
L.surfProfil = function (n) {
  n = n || 26;
  var dens = function (p, t) { var a = Math.exp(-Math.pow((p - 0.32) / 0.07, 2) / 2), b = Math.exp(-Math.pow((p - 0.72) / 0.06, 2) / 2), c = Math.exp(-Math.pow((p - 0.52) / 0.25, 2) / 2); return (1.2 - 0.6 * t) * a + (0.3 + 0.9 * t) * b + 0.18 * c; };
  return surf({ title: 'Profil de volume (schéma)', x: { name: 'heure de la séance', dom: [0, 1], fmt: function (v) { return F.pct(v, 0) + ' de la séance'; } }, y: { name: 'prix', dom: [0, 1], fmt: function (v) { return v > 0.25 && v < 0.4 ? 'HVN bas' : v > 0.64 && v < 0.8 ? 'HVN haut' : v > 0.45 && v < 0.58 ? 'creux' : 'prix ' + F.num(v * 100, 0); } },
    z: { name: 'volume cumulé', fmt: function (v) { return F.num(v, 1); } }, fn: function (t, p) { var s = 0, k = 12; for (var i = 1; i <= k; i++) s += dens(p, t * i / k); return s * t; }, mid: null }, lin(0, 1, n), lin(0, 1, n));
};

/* ---------- Schémas : de petites planches SVG, en coordonnées 0–100 ---------- */
var VW = 320, VH = 178, PL = 8, PR = 8, PT = 16, PB = 18;
function sx(x) { return +(PL + x / 100 * (VW - PL - PR)).toFixed(1); }
function sy(y) { return +(PT + (100 - y) / 100 * (VH - PT - PB)).toFixed(1); }
var E = function (t) { return T.esc(t); };
/* Densifie une ligne brisée avec un bruit déterministe (graine) : les pivots restent exacts. */
L.noisy = function (pts, amp, seed, step) {
  var r = T.rng(seed || 7), out = [pts[0]]; step = step || 2.2;
  for (var i = 1; i < pts.length; i++) {
    var a = pts[i - 1], b = pts[i], k = Math.max(1, Math.round((b[0] - a[0]) / step));
    for (var j = 1; j <= k; j++) { var t = j / k, y = a[1] + (b[1] - a[1]) * t; out.push([a[0] + (b[0] - a[0]) * t, j === k ? y : y + (r() - 0.5) * 2 * amp]); }
  }
  return out;
};
var TONE = { fg: 'var(--hi)', v: 'var(--violet)', soft: 'var(--soft)', mute: 'var(--line-2)' };
L.schemaSvg = function (o) {
  var g = '';
  g += '<rect x="' + PL + '" y="' + PT + '" width="' + (VW - PL - PR) + '" height="' + (VH - PT - PB) + '" fill="none" stroke="var(--line)" rx="4"/>';
  (o.xz || []).forEach(function (z) { g += '<rect x="' + sx(z.x0) + '" y="' + PT + '" width="' + (sx(z.x1) - sx(z.x0)) + '" height="' + (VH - PT - PB) + '" fill="rgba(255,255,255,.06)"/><text class="pl-t" x="' + ((sx(z.x0) + sx(z.x1)) / 2) + '" y="' + (PT - 4) + '" text-anchor="middle">' + E(z.label) + '</text>'; });
  (o.zones || []).forEach(function (z) {
    var x0 = sx(z.x0 == null ? 0 : z.x0), x1 = sx(z.x1 == null ? 100 : z.x1), y0 = sy(z.y1), y1 = sy(z.y0);
    g += '<rect x="' + x0 + '" y="' + y0 + '" width="' + (x1 - x0) + '" height="' + (y1 - y0) + '" fill="' + (z.tone === 'g' ? 'rgba(255,255,255,.07)' : 'var(--violet-a)') + '"' + (z.edge ? ' stroke="var(--violet-b)" stroke-dasharray="3 3"' : '') + '/>';
    if (z.label) g += '<text class="pl-t' + (z.tone === 'g' ? '' : ' v') + '" x="' + (z.right ? x1 - 4 : x0 + 4) + '" y="' + (y0 + 10) + '" text-anchor="' + (z.right ? 'end' : 'start') + '">' + E(z.label) + '</text>';
  });
  (o.lines || []).forEach(function (l) {
    var x0 = sx(l.x0 == null ? 0 : l.x0), x1 = sx(l.x1 == null ? 100 : l.x1), y = sy(l.y);
    g += '<line x1="' + x0 + '" x2="' + x1 + '" y1="' + y + '" y2="' + y + '" stroke="' + (TONE[l.tone] || TONE.soft) + '" stroke-width="' + (l.w || 1) + '"' + (l.dash ? ' stroke-dasharray="4 3"' : '') + '/>';
    if (l.label) g += '<text class="pl-t' + (l.tone === 'v' ? ' v' : '') + '" x="' + (l.left ? x0 + 3 : x1 - 3) + '" y="' + (y + (l.below ? 11 : -4)) + '" text-anchor="' + (l.left ? 'start' : 'end') + '">' + E(l.label) + '</text>';
  });
  (o.vlines || []).forEach(function (l) { var x = sx(l.x); g += '<line x1="' + x + '" x2="' + x + '" y1="' + PT + '" y2="' + (VH - PB) + '" stroke="var(--soft)" stroke-dasharray="2 3"/>' + (l.label ? '<text class="pl-t" x="' + x + '" y="' + (VH - 6) + '" text-anchor="middle">' + E(l.label) + '</text>' : ''); });
  if (o.vp) {
    var x1v = sx(100), wmax = o.vp.w || 26;
    o.vp.bins.forEach(function (b) { var y = sy(b[0]), hb = Math.max(2, (VH - PT - PB) / 100 * (o.vp.step || 4) - 1.4), w = b[1] * (sx(wmax) - sx(0)); g += '<rect x="' + (x1v - w) + '" y="' + (y - hb / 2) + '" width="' + w + '" height="' + hb + '" fill="' + (b[2] ? 'var(--violet)' : 'var(--line-2)') + '" opacity="' + (b[2] ? 0.85 : 0.9) + '"/>'; });
  }
  (o.paths || []).forEach(function (p) {
    var d = p.pts.map(function (q, i) { return (i ? 'L' : 'M') + sx(q[0]) + ',' + sy(q[1]); }).join(' ');
    g += '<path d="' + d + '" fill="none" stroke="' + (TONE[p.tone] || TONE.fg) + '" stroke-width="' + (p.w || 1.6) + '" stroke-linejoin="round" stroke-linecap="round"' + (p.dash ? ' stroke-dasharray="4 3"' : '') + '/>';
  });
  if (o.fp) g += '<text class="pl-t" x="' + (VW - PR - 4) + '" y="' + (PT + 11) + '" text-anchor="end">gris : bid · violet : ask</text>';
  if (o.fp) o.fp.forEach(function (bar) {
    var cx = sx(bar.x), half = sx(bar.half || 17) - sx(0);
    g += '<line x1="' + cx + '" x2="' + cx + '" y1="' + sy(bar.rows[0].y + 3) + '" y2="' + sy(bar.rows[bar.rows.length - 1].y - 3) + '" stroke="var(--line-2)"/>';
    bar.rows.forEach(function (r) {
      var y = sy(r.y), hb = (VH - PT - PB) / 100 * 5.4;
      g += '<rect x="' + (cx - r.b * half) + '" y="' + (y - hb / 2) + '" width="' + (r.b * half) + '" height="' + hb + '" fill="var(--soft)" opacity=".75"/>';
      g += '<rect x="' + cx + '" y="' + (y - hb / 2) + '" width="' + (r.a * half) + '" height="' + hb + '" fill="var(--violet)" opacity=".85"/>';
      if (r.hl) g += '<rect x="' + (cx - half - 2) + '" y="' + (y - hb / 2 - 1.5) + '" width="' + (2 * half + 4) + '" height="' + (hb + 3) + '" fill="none" stroke="var(--hi)" stroke-width="1.2" rx="2"/>';
    });
    if (bar.label) g += '<text class="pl-t" x="' + cx + '" y="' + (VH - 6) + '" text-anchor="middle">' + E(bar.label) + '</text>';
  });
  (o.dots || []).forEach(function (d) {
    var x = sx(d.x), y = sy(d.y), col = TONE[d.tone] || TONE.v;
    g += d.ring ? '<circle cx="' + x + '" cy="' + y + '" r="5" fill="none" stroke="' + col + '" stroke-width="1.5"/>' : '<circle cx="' + x + '" cy="' + y + '" r="3.2" fill="' + col + '"/>';
    if (d.label) { var pos = d.pos || 't', tx = pos === 'r' ? x + 7 : pos === 'l' ? x - 7 : x, ty = pos === 't' ? y - 8 : pos === 'b' ? y + 15 : y + 3.5; g += '<text class="pl-t' + (d.tone === 'fg' ? ' w' : d.tone === 'soft' ? '' : ' v') + '" x="' + tx + '" y="' + ty + '" text-anchor="' + (pos === 'r' ? 'start' : pos === 'l' ? 'end' : 'middle') + '">' + E(d.label) + '</text>'; }
  });
  (o.arrows || []).forEach(function (a) {
    var x = sx(a.x), y = sy(a.y), up = a.dir === 'up';
    g += '<path d="M' + (x - 5) + ',' + (y + (up ? 4 : -4)) + ' L' + x + ',' + (y + (up ? -4 : 4)) + ' L' + (x + 5) + ',' + (y + (up ? 4 : -4)) + ' Z" fill="' + (a.tone === 'soft' ? 'var(--soft)' : 'var(--violet)') + '"/>';
    if (a.label) g += '<text class="pl-t ' + (a.tone === 'soft' ? '' : 'v') + '" x="' + (x + 8) + '" y="' + (y + 3.5) + '">' + E(a.label) + '</text>';
  });
  (o.brackets || []).forEach(function (b) {
    var x = sx(b.x), y0 = sy(b.y0), y1 = sy(b.y1);
    g += '<path d="M' + (x - 3) + ',' + y0 + ' L' + x + ',' + y0 + ' L' + x + ',' + y1 + ' L' + (x - 3) + ',' + y1 + '" fill="none" stroke="var(--soft)"/><text class="pl-t" x="' + (x - 5) + '" y="' + ((y0 + y1) / 2 + 3.5) + '" text-anchor="end">' + E(b.label) + '</text>';
  });
  return '<svg class="pl-svg" viewBox="0 0 ' + VW + ' ' + VH + '" role="img" aria-label="' + E(o.aria || o.title || 'schéma') + '">' + g + '</svg>';
};

/* Les situations. Chaque planche : un titre, ce qu’on y lit, la version simple, et le dessin. */
var N = L.noisy;
L.SCHEMAS = {
  macroPublic: { t: 'Annonce publique, programmée', lire: 'Le consensus est déjà dans le prix. À l’heure dite, seul l’écart au consensus déplace le prix, en quelques secondes, dans un sens qu’on ne connaît pas avant.', k5: 'Tout le monde connaît l’heure du gâteau ; personne ne sait s’il sera bon.',
    d: { xz: [{ x0: 52, x1: 70, label: 'fenêtre interdite' }], vlines: [{ x: 56, label: '14:30' }], lines: [{ y: 48, label: 'consensus dans le prix', dash: true, tone: 'mute', x1: 54 }], paths: [{ pts: N([[3, 46], [55, 49]], 3, 11) }, { pts: N([[56, 49], [57, 80], [99, 74]], 4, 12) }, { pts: N([[56, 49], [57, 20], [99, 26]], 4, 13), tone: 'mute', dash: true }], dots: [{ x: 57, y: 80, label: 'surprise +', pos: 'r', tone: 'v' }, { x: 57, y: 20, label: 'surprise −', pos: 'r', tone: 'soft' }] } },
  macroRumeur: { t: 'Achète la rumeur, vends l’annonce', lire: 'Ceux qui croient savoir achètent avant. Le jour où la nouvelle tombe, il ne reste plus d’acheteur nouveau : ceux qui ont acheté la rumeur vendent l’annonce, même bonne.', k5: 'Quand tout le monde a déjà acheté le jouet à la mode, le jour de sa sortie personne ne fait la queue.',
    d: { vlines: [{ x: 62, label: 'annonce' }], paths: [{ pts: N([[3, 18], [20, 26], [40, 44], [58, 66], [62, 74], [70, 54], [99, 40]], 3, 21) }], dots: [{ x: 28, y: 31, label: 'achète la rumeur', pos: 't', tone: 'v' }, { x: 63, y: 74, label: 'vends l’annonce', pos: 'r', tone: 'fg' }], zones: [{ y0: 18, y1: 74, x0: 3, x1: 61, tone: 'g', label: 'déjà dans le prix' }] } },
  macroPrix: { t: 'Déjà dans le prix : rien à jouer', lire: 'Le marché a fini de se placer avant l’annonce. Un chiffre conforme au consensus ne laisse rien : le prix bouge à peine, la friction reste.', k5: 'Si on t’annonce une nouvelle que tu connais déjà, tu ne sautes pas de joie.',
    d: { vlines: [{ x: 60, label: 'annonce' }], paths: [{ pts: N([[3, 22], [30, 40], [58, 58], [99, 60]], 3, 31) }], lines: [{ y: 58, x0: 58, label: 'conforme : rien ne bouge', tone: 'v', dash: true }] } },
  macroPrive: { t: 'Information privée : elle diffuse', lire: 'Une information que peu ont entre lentement dans le prix : une pente, pas un saut. Quand elle devient publique, l’essentiel est fait.', k5: 'Un secret se répète d’oreille en oreille : la classe le sait petit à petit, pas d’un coup.',
    d: { paths: [{ pts: N([[3, 20], [99, 80]], 4, 41, 2.2) }], arrows: [{ x: 40, y: 32, dir: 'up', label: 'ceux qui savent achètent' }, { x: 58, y: 54, dir: 'up', label: 'les autres suivent', tone: 'soft' }], vlines: [{ x: 92, label: 'publique' }] } },

  dowHausse: { t: 'Tendance haussière', lire: 'Sommets et creux montants : biais acheteur. Le dernier creux montant (HL) est le niveau qui annule tout.', k5: 'Un escalier qui monte : chaque marche est plus haute que la précédente.',
    d: { paths: [{ pts: N([[4, 16], [18, 46], [29, 32], [45, 64], [56, 50], [72, 82], [83, 68], [97, 90]], 1.6, 51) }], dots: [{ x: 18, y: 46, label: 'HH', pos: 't', tone: 'fg' }, { x: 45, y: 64, label: 'HH', pos: 't', tone: 'fg' }, { x: 72, y: 82, label: 'HH', pos: 't', tone: 'fg' }, { x: 29, y: 32, label: 'HL', pos: 'b' }, { x: 56, y: 50, label: 'HL', pos: 'b' }, { x: 83, y: 68, label: 'HL', pos: 'b' }], lines: [{ y: 68, x0: 60, label: 'invalidation', tone: 'v', dash: true, below: true }] } },
  dowBaisse: { t: 'Tendance baissière', lire: 'Sommets et creux descendants : biais vendeur. Le dernier sommet descendant (LH) est le niveau qui annule tout.', k5: 'Un escalier qui descend.',
    d: { paths: [{ pts: N([[4, 86], [18, 56], [29, 70], [45, 38], [56, 52], [72, 20], [83, 34], [97, 12]], 1.6, 52) }], dots: [{ x: 18, y: 56, label: 'LL', pos: 'b', tone: 'fg' }, { x: 45, y: 38, label: 'LL', pos: 'b', tone: 'fg' }, { x: 72, y: 20, label: 'LL', pos: 'b', tone: 'fg' }, { x: 29, y: 70, label: 'LH', pos: 't' }, { x: 56, y: 52, label: 'LH', pos: 't' }, { x: 83, y: 34, label: 'LH', pos: 't' }], lines: [{ y: 34, x0: 60, label: 'invalidation', tone: 'v', dash: true }] } },
  dowRange: { t: 'Range : pas de sens', lire: 'Sommets égaux, creux égaux : aucun biais. Le plan ne donne pas de sens ; on attend, ou on applique ce qu’on a écrit d’avance pour les deux bandes.', k5: 'La balle rebondit entre deux murs : on ne sait pas de quel côté elle finira par sortir.',
    d: { zones: [{ y0: 70, y1: 80, tone: 'g', label: 'haut du range' }, { y0: 22, y1: 32, tone: 'g', label: 'bas du range' }], paths: [{ pts: N([[4, 50], [17, 76], [30, 27], [45, 75], [58, 28], [72, 77], [86, 26], [97, 52]], 1.8, 53) }] } },
  dowCassure: { t: 'Cassure de structure en séance', lire: 'La veille était haussière, mais le dernier creux montant cède : la structure de Dow a changé. Le biais est suspendu jusqu’à une nouvelle structure lisible.', k5: 'L’escalier montait, puis une marche s’effondre : on arrête de monter.',
    d: { paths: [{ pts: N([[4, 18], [18, 46], [29, 34], [45, 68], [56, 52], [66, 62], [80, 26], [97, 34]], 1.6, 54) }], dots: [{ x: 56, y: 52, label: 'dernier HL', pos: 'l', tone: 'fg' }, { x: 71.5, y: 48, ring: true, label: 'cassure', pos: 'r' }], lines: [{ y: 52, x0: 50, tone: 'v', dash: true, label: 'biais suspendu', below: true }] } },

  zoneTraverse: { t: 'Le HVN est traversé', lire: 'Le prix entre dans le HVN, ralentit, puis le traverse. Un HVN n’est pas un mur : c’est l’endroit où il hésite.', k5: 'On traverse la place pleine de monde en jouant des coudes, puis on continue.',
    d: { zones: [{ y0: 52, y1: 66, label: 'HVN', edge: true }], paths: [{ pts: N([[3, 18], [30, 50], [44, 58], [52, 54], [64, 62], [70, 72], [97, 88]], 2, 61) }], dots: [{ x: 70, y: 72, label: 'traversée', pos: 'r', tone: 'fg' }] } },
  zoneRebond: { t: 'Traversé, puis rebond dessus', lire: 'Le prix traverse, revient tester le HVN par l’autre côté, et repart. C’est le contact qui intéresse le plan : le HVN devient un appui.', k5: 'On saute par-dessus la flaque, puis on se repose sur son bord avant de repartir.',
    d: { zones: [{ y0: 44, y1: 58, label: 'HVN', edge: true }], paths: [{ pts: N([[3, 16], [26, 52], [38, 74], [52, 60], [60, 56], [70, 70], [97, 86]], 1.8, 62) }], dots: [{ x: 60, y: 56, label: 'contact : le setup', pos: 'b', tone: 'v' }] } },
  zoneIgnore: { t: 'Le prix n’y vient pas', lire: 'Le HVN reste loin toute la séance. Rien à faire : un plan qui force le contact invente des trades.', k5: 'Le ballon n’est jamais venu dans ton camp : tu n’avais rien à faire.',
    d: { zones: [{ y0: 70, y1: 84, label: 'HVN', edge: true }], paths: [{ pts: N([[3, 30], [20, 44], [36, 34], [52, 50], [70, 38], [86, 52], [97, 44]], 3, 63) }], lines: [{ y: 60, label: 'jamais atteinte', tone: 'mute', dash: true, x0: 50 }] } },

  gexPortee: { t: 'La cible est dans la portée', lire: 'Le premier niveau GEX dans le sens du trade, à une distance que la séance parcourt souvent. L’objectif se pose juste avant la zone, là où les autres prennent leurs gains.', k5: 'Le drapeau est assez près pour qu’on l’atteigne avant la fin de la récré.',
    d: { zones: [{ y0: 66, y1: 80, label: 'zone GEX', right: true }], lines: [{ y: 64, label: 'objectif', tone: 'v', left: true }, { y: 26, label: 'entrée', tone: 'fg', left: true }, { y: 16, label: 'stop', tone: 'soft', dash: true, left: true }], paths: [{ pts: N([[22, 26], [40, 40], [52, 36], [70, 58], [80, 64]], 2, 71) }], brackets: [{ x: 97, y0: 26, y1: 64, label: 'portée' }] } },
  gexLoin: { t: 'La cible est hors de portée', lire: 'Un niveau plus loin que ce qu’une séance parcourt n’arrive presque jamais avant la cloche : la partie XXX d’ALP nº 3 montre qu’un objectif hors de portée vaut zéro, pas sa probabilité théorique. On vise le HVN opposé.', k5: 'Le drapeau est de l’autre côté de la ville : la récré finit avant.',
    d: { zones: [{ y0: 86, y1: 96, label: 'GEX lointain', right: true, tone: 'g' }, { y0: 52, y1: 62, label: 'HVN opposé', right: true }], lines: [{ y: 50, label: 'objectif réel', tone: 'v', left: true }, { y: 22, label: 'entrée', tone: 'fg', left: true }], paths: [{ pts: N([[22, 22], [44, 38], [60, 32], [84, 50]], 2, 72) }], brackets: [{ x: 97, y0: 22, y1: 66, label: 'portée' }] } },
  gexZone: { t: 'Un niveau GEX est une zone', lire: 'La courbure d’une option tombe à la moitié de son sommet à 1,177 σ√T du strike : le niveau a une largeur, qui grandit avec l’échéance. Ni entrée ni stop sur le trait.', k5: 'Le niveau n’est pas un fil : c’est un coussin.',
    d: { zones: [{ y0: 40, y1: 64, label: '± 1,177 σ√T', edge: true }], lines: [{ y: 52, label: 'strike publié', tone: 'fg', dash: true }], paths: [{ pts: N([[3, 20], [30, 44], [42, 58], [50, 47], [62, 61], [74, 45], [97, 62]], 2, 73) }] } },

  risqueStop: { t: 'Stop au-delà de la zone', lire: 'Entrée au bord de la zone, stop de l’autre côté de toute la zone, plus une marge en ticks. La taille se calcule sur cette distance, pas l’inverse.', k5: 'Le filet est sous le trampoline, pas au milieu.',
    d: { zones: [{ y0: 34, y1: 48, label: 'zone', edge: true }], lines: [{ y: 48, label: 'entrée', tone: 'fg', left: true }, { y: 28, label: 'stop : zone + marge', tone: 'v', dash: true, left: true }, { y: 80, label: 'objectif', tone: 'v', left: true }], paths: [{ pts: N([[30, 72], [44, 50], [52, 42], [58, 48], [76, 66], [92, 80]], 1.8, 91) }], brackets: [{ x: 98, y0: 28, y1: 48, label: 'risque' }] } },
  risqueBruit: { t: 'Stop dans la zone : pris par le bruit', lire: 'Un stop posé dans la zone se fait toucher par une mèche ordinaire, puis le prix part sans toi. La zone a une largeur : le stop la respecte.', k5: 'Si le filet est trop haut, le premier rebond normal le touche.',
    d: { zones: [{ y0: 34, y1: 48, label: 'zone', edge: true }], lines: [{ y: 42, label: 'stop trop serré', tone: 'soft', dash: true, left: true }], paths: [{ pts: N([[22, 70], [40, 50], [48, 38], [54, 46], [70, 64], [92, 84]], 1.6, 92) }], dots: [{ x: 47.2, y: 39, ring: true, label: 'stoppé', pos: 'l', tone: 'v' }] } },
  risqueFins: { t: 'Une position a trois fins', lire: 'Le stop, l’objectif, et la cloche : la séance se ferme avant que l’un des deux soit touché. ALP nº 3, partie XXX : à stop large, la cloche prend jusqu’à 28,5 % des issues. Le relief chiffre les trois.', k5: 'La partie finit de trois façons : on gagne, on perd, ou la cloche sonne avant.',
    d: { vlines: [{ x: 90, label: 'cloche' }], lines: [{ y: 82, label: 'objectif', tone: 'v', left: true, x1: 90 }, { y: 18, label: 'stop', tone: 'soft', dash: true, left: true, x1: 90 }], paths: [{ pts: N([[10, 50], [30, 66], [44, 82]], 2, 93) }, { pts: N([[10, 50], [26, 36], [40, 18]], 2, 94), tone: 'soft' }, { pts: N([[10, 50], [40, 56], [70, 44], [90, 54]], 2, 95), tone: 'mute' }], dots: [{ x: 44, y: 82, tone: 'v' }, { x: 40, y: 18, tone: 'soft' }, { x: 90, y: 54, tone: 'fg', label: 'cloche', pos: 'l' }] } }
};

/* =====================================================================
   2. Interface
   ===================================================================== */
var CSS = '.pl-svg{display:block;width:100%;height:auto}.pl-t{font:500 9.5px var(--f-mono);fill:var(--soft)}.pl-t.v{fill:var(--violet-2)}.pl-t.w{fill:var(--hi)}' +
  '.pl-grid{display:grid;gap:12px;min-width:0}@media(min-width:760px){.pl-grid{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}}' +
  '.pl-sit{display:flex;flex-direction:column;gap:8px;min-width:0}.pl-sit p{margin:0;font-size:13px;line-height:1.5;color:var(--fg)}.pl-car .k5,.pl-now .k5{color:var(--soft);font-family:var(--f-serif);font-style:italic;font-size:15px;line-height:1.35}' +
  '.pl-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.pl-back{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line-2);border-radius:999px;padding:6px 12px;background:var(--panel);color:var(--fg);font-size:12.5px}' +
  '.pl-ring{position:relative;width:64px;height:64px;flex:none}.pl-ring svg{width:64px;height:64px}.pl-ring b{position:absolute;inset:0;display:grid;place-items:center;font:600 15px var(--f-mono);color:var(--hi)}' +
  '.pl-sum{display:flex;gap:14px;align-items:center}.pl-sum .tx{display:flex;flex-direction:column;gap:3px;min-width:0}.pl-sum .tx b{color:var(--hi);font-size:15px}.pl-sum .tx span{color:var(--soft);font-size:12.5px;line-height:1.4}' +
  '.pl-quoi{display:grid;gap:8px}.pl-q{display:grid;grid-template-columns:22px minmax(0,1fr);gap:2px 10px;align-items:start;padding:10px 12px;border:1px solid var(--line);border-radius:var(--r);background:var(--panel)}.pl-q i{font:600 11px/22px var(--f-mono);color:var(--violet-2);font-style:normal}.pl-q b{color:var(--hi);font-size:13.5px}.pl-q span{grid-column:2;color:var(--soft);font-size:12.5px;line-height:1.45}.pl-q .btn{grid-column:2;justify-self:start;margin-top:6px}' +
  '.pl-k5{border-left:2px solid var(--violet);padding:4px 0 4px 12px;margin:0;font-family:var(--f-serif);font-style:italic;font-size:17px;line-height:1.35;color:var(--fg)}' +
  '.pl-valid{display:flex;flex-direction:column;gap:8px;margin-top:6px}.pl-valid .btn{width:100%;justify-content:center;padding:14px;font-size:14px}' +
  '.pl-live{display:grid;gap:8px}.pl-lc{display:grid;grid-template-columns:30px minmax(0,1fr);gap:2px 12px;align-items:center;text-align:left;padding:13px 14px;border:1px solid var(--line);border-radius:var(--r);background:var(--panel);color:var(--fg);width:100%}.pl-lc i{width:26px;height:26px;border-radius:8px;border:1.5px solid var(--line-2);display:grid;place-items:center;font:700 14px/1 var(--f-mono);font-style:normal;color:var(--ink)}.pl-lc b{font-size:14.5px;color:var(--hi)}.pl-lc span{grid-column:2;color:var(--soft);font-size:12px;line-height:1.4}' +
  '.pl-lc[aria-checked="true"]{border-color:var(--violet-b);background:var(--violet-a)}.pl-lc[aria-checked="true"] i{background:var(--violet);border-color:var(--violet)}.pl-lc.auto{cursor:default}.pl-lc.no i{border-color:var(--soft)}' +
  '.pl-valid .btn,.pl-go .btn{height:auto;min-height:50px;white-space:normal;line-height:1.3}.pl-go{display:grid;grid-template-columns:1fr 1fr;gap:8px}.pl-go .btn{justify-content:center;padding:16px 10px;font-size:15px}.pl-go .wide{grid-column:1/-1}' +
  '.pl-verdict{display:flex;align-items:center;gap:12px;padding:14px;border-radius:var(--r);border:1px solid var(--line-2);background:var(--raise)}.pl-verdict b{flex:none;white-space:nowrap;font:600 13px var(--f-mono);letter-spacing:.08em;color:var(--hi)}.pl-verdict span{color:var(--soft);font-size:13px;line-height:1.4}.pl-verdict.ok{border-color:var(--violet);background:var(--violet-a)}.pl-verdict.ok b{color:var(--violet-2)}' +
  '.pl-ord{counter-reset:o;display:grid;gap:8px;margin:0;padding:0;list-style:none}.pl-ord li{display:grid;grid-template-columns:26px minmax(0,1fr);gap:2px 10px;padding:10px 12px;border:1px solid var(--line);border-radius:var(--r);background:var(--panel)}.pl-ord li:before{counter-increment:o;content:counter(o);font:600 11px/22px var(--f-mono);color:var(--violet-2)}.pl-ord b{color:var(--hi);font-size:13.5px}.pl-ord span{grid-column:2;color:var(--soft);font-size:12.5px;line-height:1.45}' +
  '.pl-mos{display:grid;gap:14px}.pl-mo{display:flex;flex-direction:column;gap:10px;padding:14px;border:1px solid var(--line);border-radius:var(--r);background:var(--panel);min-width:0}.pl-mo.on{border-color:var(--violet-b)}' +
  '.pl-mh{display:grid;grid-template-columns:30px minmax(0,1fr) auto;gap:10px;align-items:center;text-align:left;width:100%;padding:0;background:none;border:0;color:var(--fg)}.pl-mh i{width:28px;height:28px;border-radius:8px;border:1.5px solid var(--line-2);display:grid;place-items:center;font:700 12px/1 var(--f-mono);font-style:normal;color:var(--soft)}.pl-mo.on .pl-mh i{background:var(--violet);border-color:var(--violet);color:var(--ink)}.pl-mh b{font-size:15.5px;color:var(--hi);line-height:1.25}.pl-mh span{font:600 10px var(--f-mono);letter-spacing:.08em;text-transform:uppercase;color:var(--mute)}.pl-mo.on .pl-mh span{color:var(--violet-2)}' +
  '.pl-vf{margin:0;font-size:13.5px;line-height:1.5;color:var(--fg)}.pl-vf .pl-tag{margin-right:8px}' +
  '.pl-carw{min-width:0}.pl-car{display:flex;gap:10px;overflow-x:auto;scroll-snap-type:x mandatory;padding-bottom:4px;-webkit-overflow-scrolling:touch}.pl-car>*{flex:0 0 88%;scroll-snap-align:start;min-width:0}.pl-car.one>*{flex-basis:100%}.pl-hint{font:500 10.5px var(--f-mono);color:var(--mute);margin-top:6px}' +
  '@media(min-width:900px){.pl-car{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));overflow:visible}.pl-car>*{flex:none}.pl-car.one{grid-template-columns:minmax(0,1fr)}.pl-hint{display:none}}' +
  '.pl-fig{min-width:0}.pl-fig svg{display:block;width:100%;height:auto}.pl-n{font:500 10px var(--f-mono);fill:var(--fg)}.card p.pl-ill,.pl-ill{margin:0;font-size:11.5px;line-height:1.45;color:var(--mute)}' +
  '.pl-badge{align-self:flex-start;font:600 10.5px var(--f-mono);letter-spacing:.06em;text-transform:uppercase;padding:5px 9px;border-radius:999px;border:1px solid var(--line-2);color:var(--soft)}.pl-badge.ok{border-color:var(--violet);color:var(--violet-2);background:var(--violet-a)}' +
  '.pl-now{display:flex;flex-direction:column;gap:10px;padding:12px;border:1px solid var(--violet-b);border-radius:var(--r);background:var(--raise)}.pl-nowh{display:flex;flex-direction:column;gap:4px}.pl-nowh b{color:var(--hi);font-size:15px}.pl-nowh span{color:var(--soft);font-size:13px;line-height:1.4}.pl-lc.cur{border-color:var(--violet)}' +
  '.pl-flds .fld textarea{min-height:44px}.pl-tag{font:600 10px var(--f-mono);letter-spacing:.12em;text-transform:uppercase;color:var(--violet-2)}';
function injectCss() { if (document.getElementById('plan-css')) return; var s = document.createElement('style'); s.id = 'plan-css'; s.textContent = CSS; document.head.appendChild(s); }
L.injectCss = injectCss;

function getDay() { return L.normDay(T.store.get(K.day, null), T.day.key()); }
function saveDay(d) { T.store.set(K.day, d); }
function getPrefs() { return L.normPrefs(T.store.get(K.prefs, null)); }
function savePrefs(p) { T.store.set(K.prefs, p); }
function pctOf(id) { return T.day.pct(id); }
/* Le pourcentage de l’étape suit sa liste : 100 % la marque faite, une case décochée la défait. */
function syncPct(day, id) {
  var p = L.ownPct(day, id), d = T.day.get();
  T.day.setPct(id, p);
  if (p >= 100 && !d.done[id]) T.day.mark(id);
  else if (p < 100 && d.done[id] && d.pct[id] === 100) T.day.mark(id, false);
}
function bias(day) { return L.biasOf(day.veille, day.dow); }
function events(day) { return L.parseTimes(day.annonces); }
function nowMin() { var p = T.time.parts('Europe/Paris'); return p.h * 60 + p.m; }
function fenetre(day, prefs) { return L.forbidden(nowMin(), events(day), prefs.avant, prefs.apres); }
/* Le biais du plan est aussi celui du desk NQ (et donc du desk Stratégie intraday). */
function writeBias(day) {
  var b = bias(day), today = T.day.key(), cur = T.store.get(K.nqBias, null);
  var base = cur && cur.date === today ? cur : { date: today, checks: {} };
  if ((base.bias || null) === (b || null)) return;
  T.store.set(K.nqBias, Object.assign({}, base, { date: today, at: Date.now(), bias: b }));
}
function gexLevels() {
  var st = T.store.get(K.nqGex, null), nq = T.lib.nq;
  if (!st || st.date !== T.day.key() || !st.text || !nq || !nq.parseGex) return [];
  try { var r = nq.parseGex(st.text, st.price, st.base, { bandePct: st.bande, appliquer: st.appliquer }); return (r.niveaux || []).filter(function (x) { return fin(x.nq); }).map(function (x) { return { price: x.nq, label: x.code || 'GEX' }; }); } catch (e) { return []; }
}
function gammaOf(day) { var gx = gexLevels(); if (!gx.length) gx = L.parseLevels(day.gexMan, 'GEX').map(function (z) { return { price: z.mid, label: z.label.slice(0, 8) }; }); return gx; }
function dayLevels(day) {
  var out = [];
  L.parseLevels(day.hvn, 'HVN').forEach(function (z, i) { out.push({ price: z.mid, label: 'HVN' + (i + 1), kind: 'violet', zone: z }); });
  gammaOf(day).forEach(function (g) { out.push({ price: g.price, label: String(g.label).slice(0, 8), kind: 'mute', dash: true }); });
  if (fin(day.prix)) out.push({ price: day.prix, label: 'prix', kind: null });
  return out;
}
/* La carte du jour : tendance, HVN, gamma et prix saisis → setups candidats, et le meilleur. */
function dayCarte(day, prefs) {
  var hv = L.parseLevels(day.hvn, 'HVN').map(function (z, i) { return Object.assign({}, z, { label: 'HVN ' + (i + 1) }); });
  var list = L.setups({ bias: bias(day), price: day.prix, hvn: hv, gamma: gammaOf(day), marge: prefs.marge, tick: prefs.tick, range: prefs.range, rrMin: prefs.rrMin });
  return { hvn: hv, gamma: gammaOf(day), list: list, best: L.best(list, prefs.rrMin) };
}

function ring(p) {
  var r = 27, c = 2 * Math.PI * r, off = c * (1 - Math.max(0, Math.min(100, p)) / 100);
  var el = h('div', { class: 'pl-ring' }); el.innerHTML = '<svg viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="' + r + '" fill="none" stroke="var(--line)" stroke-width="5"/><circle cx="32" cy="32" r="' + r + '" fill="none" stroke="var(--violet)" stroke-width="5" stroke-linecap="round" stroke-dasharray="' + c.toFixed(2) + '" stroke-dashoffset="' + off.toFixed(2) + '" transform="rotate(-90 32 32)"/></svg>';
  el.appendChild(h('b', null, p + ' %')); return el;
}

/* Où j’en suis : la préparation, la tendance, le sens, les limites, la prochaine fenêtre interdite. */
function summary(ctx, day, prefs) {
  var set = ctx.settings, b = bias(day), rule = L.sideRule(b), st = L.todayStats(T.journal.list(), T.day.key());
  var prep = L.prepPct(pctOf), fw = fenetre(day, prefs), left = Math.max(0, set.dailyStop + Math.min(0, st.pnl));
  var stop = st.losses >= set.maxLossesDay || st.taken >= set.maxTradesDay || left <= 0, cr = dayCarte(day, prefs);
  var fwText = fw.now ? 'Fenêtre interdite : ' + fw.now.ev.label + ' ' + fw.now.ev.hhmm + ', jusqu’à ' + L.minText(fw.now.until) : fw.next ? 'Prochaine fenêtre interdite : ' + L.minText(fw.next.from) + ' (' + fw.next.ev.label + ')' : events(day).length ? 'Plus d’annonce aujourd’hui' : 'Aucune annonce saisie (étape Macro)';
  var setupText = cr.best ? 'Setup : ' + (cr.best.side > 0 ? 'achat' : 'vente') + ' au ' + cr.best.zone.label + ' → ' + cr.best.label + ', R:R 1:' + F.num(cr.best.rr, cr.best.rr < 10 ? 1 : 0) : b === 'both' ? 'Tendance neutre : pas de setup' : 'Pas encore de setup sur la carte';
  return h('div', { class: 'card accent' }, h('div', { class: 'cb' },
    h('div', { class: 'pl-sum' }, ring(prep), h('div', { class: 'tx' }, h('b', null, stop ? 'Journée finie : limite atteinte' : 'Préparation ' + prep + ' %'), h('span', null, (b ? 'Tendance ' + L.biasWord(b) + ' · ' + rule.short : 'Tendance à déclarer')), h('span', null, setupText), h('span', null, fwText))),
    U.kpis([
      { label: 'Trades', value: st.taken + ' / ' + set.maxTradesDay, tone: st.taken >= set.maxTradesDay ? 'neg' : null, hint: 'pris aujourd’hui' },
      { label: 'Pertes', value: st.losses + ' / ' + set.maxLossesDay, tone: st.losses >= set.maxLossesDay ? 'neg' : null, hint: 'avant l’arrêt' },
      { label: 'Risque restant', value: F.usd(left, 0), tone: left <= 0 ? 'neg' : null, hint: 'stop du jour ' + F.usd(set.dailyStop, 0) },
      { label: 'À compléter', value: String(st.open), tone: st.open ? 'acc' : null, hint: 'au journal, après', onClick: st.open ? function () { T.nav.go('journal', 'registre'); } : null }
    ], 4)));
}

/* ---------- Figures : une carte par figure, dans un carrousel qu’on fait glisser ---------- */
function PF() { return T.lib.planFig; }
function sgn(v) { return (v > 0 ? '+' : v < 0 ? '−' : '') + F.int(Math.abs(v)); }
function marked(bar, col) { return bar.rows.filter(function (r) { return r[3]; }).map(function (r) { return F.int(r[col]); }); }
L.VK = 1.5; /* le contact marqué sur les planches VWAP : la première bande ; ±2,5σ est tracée aussi */
L.VTXT = {
  achat: { t: 'Tendance haussière : contact de la bande basse', lire: function () { return 'Le prix descend toucher −1,5σ, puis s’approche de −2,5σ : c’est le seul côté où le plan cherche un achat, sur un HVN et avec un mur. Il revient ensuite vers la VWAP.'; } },
  vente: { t: 'Tendance baissière : contact de la bande haute', lire: function () { return 'Le miroir : le prix monte toucher +1,5σ, seul côté où le plan cherche une vente, puis revient vers la VWAP.'; } },
  attendre: { t: 'Tendance haussière, prix au-dessus', lire: function () { return 'Le prix reste au-dessus de la VWAP toute la séance : aucune bande basse touchée, donc aucun achat. On ne court pas après le prix.'; } },
  neutre: { t: 'Ta VWAP et ses bandes ±1,5σ, ±2,5σ', lire: function () { return 'La ligne blanche est la VWAP ancrée à minuit ; les quatre courbes grises sont les bandes à ±1,5σ et ±2,5σ, qui s’ouvrent quand le prix s’écarte. Ici le prix tourne autour de la VWAP : en tendance neutre, même un contact ne se joue pas.'; } },
  ouverture: { t: 'Choc à l’ouverture américaine', lire: function () { return 'À 15 h 30 le prix plonge et touche les bandes basses en quelques minutes, pendant la fenêtre interdite : les bandes s’ouvrent, ce contact ne se joue pas.'; } }
};
L.vMarks = function (name, m, k) {
  if (!m) return [];
  var kk = String(k).replace('.', ',');
  if (name === 'achat') return [{ i: m.i, at: 'l', label: 'contact −' + kk + 'σ', pos: 'b' }].concat(m.j > 0 ? [{ i: m.j, at: 'h', label: 'retour VWAP', pos: 't' }] : []);
  if (name === 'vente') return [{ i: m.i, at: 'h', label: 'contact +' + kk + 'σ', pos: 't' }].concat(m.j > 0 ? [{ i: m.j, at: 'l', label: 'retour VWAP', pos: 'b' }] : []);
  if (name === 'ouverture') return [{ i: m.i, at: 'l', label: 'fenêtre : pas d’ordre', pos: 'b' }];
  return [];
};
L.FPTXT = {
  absorptionAcheteuse: { t: 'Absorption acheteuse, chiffrée', lire: function (b) { return 'Barre d’arrivée : ' + marked(b[0], 1).join(', ') + ' contrats vendus au bid dans la zone (cellules entourées), et le prix ne descend pas plus bas. Delta ' + sgn(PF().fpStats(b[0].rows).delta) + ' sans progrès : un acheteur passif absorbe tout. La barre suivante repart, delta ' + sgn(PF().fpStats(b[1].rows).delta) + '.'; } },
  absorptionVendeuse: { t: 'Absorption vendeuse, chiffrée', lire: function (b) { return 'Le miroir à la résistance : ' + marked(b[0], 2).join(', ') + ' contrats achetés à l’ask, et le prix ne monte plus. Delta ' + sgn(PF().fpStats(b[0].rows).delta) + ' sans progrès : un vendeur passif absorbe. Barre suivante, delta ' + sgn(PF().fpStats(b[1].rows).delta) + ', le prix redescend.'; } },
  epuisement: { t: 'Épuisement, chiffré', lire: function (b) { var lo = b[0].rows[b[0].rows.length - 1]; return 'Au bas de la barre d’arrivée, les derniers prix n’échangent presque plus : ' + lo[1] + ' × ' + lo[2] + ' au plus bas. Il ne reste plus de vendeurs. La barre suivante ne prolonge pas et repart, delta ' + sgn(PF().fpStats(b[1].rows).delta) + '.'; } },
  recharge: { t: 'Mur qui se recharge (iceberg), chiffré', lire: function (b) { var r = b[0].rows[b[0].rows.length - 1]; return 'Au niveau de la zone, ' + F.int(r[1]) + ' contrats vendus au bid alors que le mur n’en affichait qu’environ 300 : il se reforme à chaque frappe. Absorption cachée, plus forte qu’affichée.'; } },
  mangee: { t: 'La zone cède : continuation, chiffrée', lire: function (b) { return 'Gros volume au bid dans la zone (' + marked(b[0], 1).join(', ') + '), puis la barre suivante casse en dessous avec encore ' + marked(b[1], 1).join(', ') + ' au bid : les vendeurs gagnent, delta ' + sgn(PF().fpStats(b[1].rows).delta) + '. En tendance baissière, c’est une continuation ; en tendance haussière, pas d’achat.'; } },
  retiree: { t: 'Mur retiré, chiffré', lire: function (b) { return 'Au niveau où le mur était affiché, presque rien ne s’échange : ' + b[1].rows.filter(function (r) { return r[3]; }).map(function (r) { return r[1] + ' × ' + r[2]; }).join(' puis ') + '. Il n’y avait plus personne : le prix traverse.'; } },
  initiative: { t: 'Initiative : déséquilibres empilés', lire: function (b) { return 'Trois prix d’affilée où l’ask domine le bid d’au moins trois contre un (cellules entourées, à droite) : des acheteurs agressifs cassent la résistance, delta ' + sgn(PF().fpStats(b[1].rows).delta) + '. En tendance haussière, c’est la continuation ; ne vends jamais contre ça.'; } },
  invalidation: { t: 'Absorption, puis invalidation', lire: function (b) { return 'Absorption au contact (' + marked(b[0], 1).join(', ') + ' au bid), puis la barre suivante clôture sous la zone, delta ' + sgn(PF().fpStats(b[1].rows).delta) + ' : sortie immédiate.'; } }
};
L.LIQ_OK = { tient: true, resistance: true, recharge: true, epuisement: true, continuation: true };
function svgBox(svg) { var d = h('div', { class: 'pl-fig' }); d.innerHTML = svg; return d; }
function figCard(f, ctx, day, prefs) {
  var G = PF(), k = L.VK;
  if (f.s) { var s = L.SCHEMAS[f.s]; if (!s) return null; return U.card({ title: s.t, body: [svgBox(L.schemaSvg(Object.assign({ aria: s.t }, s.d))), h('p', null, s.lire), h('p', { class: 'k5' }, s.k5)] }); }
  if (f.v) { var sc = G.scen(f.v, k), vt = L.VTXT[f.v]; if (!sc) return null; return U.card({ title: vt.t, meta: '±1,5σ et ±2,5σ', body: [svgBox(G.vwapSvg(sc, { k: k, marks: L.vMarks(f.v, sc.m, k), zone: f.v === 'ouverture' ? sc.m : null, aria: vt.t })), h('p', null, vt.lire(k)), h('p', { class: 'pl-ill' }, G.DISCLAIMER)] }); }
  if (f.fp) { var fp = G.FP[f.fp], ft = L.FPTXT[f.fp]; return U.card({ title: ft.t, meta: 'bid × ask', body: [svgBox(G.fpSvg(Object.assign({ aria: ft.t }, fp))), h('p', null, ft.lire(fp.bars)), h('p', { class: 'pl-ill' }, 'Gauche : vendu au bid. Droite : acheté à l’ask. Sous la barre : delta (ask − bid) et volume, calculés. ' + G.DISCLAIMER)] }); }
  if (f.liq) {
    var c = G.LIQ[f.liq], ok = !!L.LIQ_OK[f.liq], body = [h('div', { class: 'pl-badge' + (ok ? ' ok' : '') }, f.liq === 'continuation' ? 'Trade dans le sens de la tendance' : ok ? 'Trade possible' : 'Pas de trade'), svgBox(G.heatSvg(f.liq))];
    if (c.fp) body.push(svgBox(G.fpSvg(Object.assign({ aria: c.t }, G.FP[c.fp]))));
    body.push(h('p', null, h('b', null, 'Ce qu’on voit. '), c.lire)); body.push(h('p', null, h('b', null, 'Ce qu’on fait. '), c.faire));
    body.push(h('p', { class: 'pl-ill' }, 'En haut, le carnet dans le temps : la teinte dit la taille affichée, les cercles le volume échangé. En bas, le footprint du contact. ' + G.DISCLAIMER));
    return U.card({ title: c.t, accent: ok, body: body });
  }
  if (f.carte) {
    var cr = dayCarte(day, prefs), b = cr.best;
    var txt = !bias(day) ? 'Déclare la tendance (étape 2) : sans elle, la carte ne sait pas de quel côté chercher.' : bias(day) === 'both' ? 'Tendance neutre : la carte ne trace aucun setup, et c’est la bonne réponse.' : !fin(day.prix) ? 'Saisis le prix du moment (étape Setup) pour placer la carte.' : !cr.hvn.length || !cr.gamma.length ? 'Il manque des HVN ou des niveaux gamma : la carte trace ce qu’elle a.' : b ? (b.side > 0 ? 'Achat' : 'Vente') + ' au bord du ' + b.zone.label + ' (' + F.num(b.entry, 2) + '), stop ' + F.num(b.stop, 2) + ' derrière lui, cible ' + b.label + ' ' + F.num(b.target, 2) + ' : R:R 1:' + F.num(b.rr, 1) + (b.pObjectif != null ? ', objectif atteint dans la séance ' + F.pct(b.pObjectif, 1) + ' du temps sans avantage.' : '.') : 'Aucun couple HVN–gamma ne passe ton R:R minimal (' + F.num(prefs.rrMin, 1) + ') dans la portée de la séance : pas de setup à ce prix.';
    return U.card({ title: 'Ta carte du jour', meta: 'tes niveaux', accent: !!b, body: [svgBox(G.carteSvg({ price: day.prix, hvn: cr.hvn, gamma: cr.gamma, best: b })), h('p', null, txt), h('p', { class: 'pl-ill' }, 'Calculée avec tes saisies : tendance, HVN, niveaux gamma, prix, marge de stop. Probabilité sans dérive (aucun avantage supposé), à la portée de la séance que tu as saisie.')] });
  }
  if (f.vp) return U.card({ title: 'Le profil de volume d’hier', meta: 'calculé', body: [svgBox(G.vpSvg()), h('p', null, 'Le profil compte le volume échangé à chaque prix. Ses bosses (en violet) sont les HVN ; la barre blanche est le POC, le prix le plus échangé. Les HVN sont détectés par une règle, pas posés à la main.'), h('p', { class: 'pl-ill' }, G.DISCLAIMER)] });
  if (f.day) { var ev = events(day); return U.card({ title: 'Ta journée', meta: 'heure de Paris', body: [svgBox(G.daySvg(ev, prefs.avant, prefs.apres, nowMin())), h('p', null, ev.length ? 'En violet, les fenêtres interdites : ' + prefs.avant + ' min avant et ' + prefs.apres + ' min après chaque annonce. Le trait blanc est l’heure présente.' : 'Aucune annonce saisie : la frise montre seulement la séance cash américaine. Écris les annonces du jour pour poser les fenêtres.')] }); }
  if (f.ladder) { var lv = dayLevels(day); return U.card({ title: 'Tes niveaux du jour', meta: lv.length + ' niveau' + (lv.length > 1 ? 'x' : ''), body: lv.length ? [T.chart.ladder({ levels: lv, height: Math.max(200, lv.length * 26 + 24), fmt: function (v) { return F.num(v, 2); } }), h('p', { class: 'pl-ill' }, 'Violet : HVN (milieu de la fourchette). Pointillé gris : niveaux gamma. Le prix, s’il est saisi.')] : [U.note('Rien de noté pour l’instant : tes HVN et niveaux gamma apparaîtront ici à mesure que tu les écris.')] }); }
  if (f.relief) return relief(f.relief);
  return null;
}
/* L’ordre des planches : la situation choisie (ou celle de la tendance) passe en premier. */
L.sortFigs = function (figs, day) {
  var b = L.biasOf(day.veille, day.dow), score = function (f) { if (f.sel && (f.sel === day.veille || f.sel === day.dow)) return 0; if (f.bias && b && f.bias === b) return 0; if (f.bias && b && f.bias !== b) return 2; return 1; };
  return figs.map(function (f, i) { return { f: f, i: i, s: score(f) }; }).sort(function (a, c) { return a.s - c.s || a.i - c.i; }).map(function (x) { return Object.assign({}, x.f, { chosen: x.s === 0 }); });
};
function carousel(figs, ctx, day, prefs) {
  var cards = L.sortFigs(figs, day).map(function (f) { var c = figCard(f, ctx, day, prefs); if (c && f.chosen) c.classList.add('accent'); return c; }).filter(Boolean);
  if (!cards.length) return null;
  var wrap = h('div', { class: 'pl-carw' }), car = h('div', { class: 'pl-car' + (cards.length === 1 ? ' one' : '') }, cards);
  wrap.appendChild(car);
  if (cards.length > 1) wrap.appendChild(h('div', { class: 'pl-hint' }, cards.length + ' planches · glisse pour les voir'));
  return wrap;
}
function relief(kind) {
  var P = T.lib.perf; if (!P || !P.charts || !P.charts.surface3d) return U.card({ title: 'Relief', body: U.note('Le relief demande le desk Métriques.') });
  P.injectCss && P.injectCss();
  var cas = T.store.get(K.view + ':liqcas', 'tient'), view = T.store.get(K.view + ':' + kind, '3d'), box = h('div');
  function sf() { return kind === 'fins' ? L.surfFins() : kind === 'delai' ? L.surfDelai() : kind === 'gros' ? L.surfGros() : kind === 'liq' ? PF().surfLiq(cas) : L.surfProfil(); }
  function paint() {
    T.clear(box); var s = sf();
    if (kind === 'liq') box.appendChild(U.chips({ options: [['tient', 'Tient'], ['recharge', 'Se recharge'], ['spawn', 'Apparu d’un coup'], ['retiree', 'Retiré'], ['mangee', 'Mangé']].map(function (o) { return { v: o[0], label: o[1] }; }), value: cas, onChange: function (v) { cas = v; T.store.set(K.view + ':liqcas', v); paint(); } }));
    box.appendChild(U.seg({ aria: 'Rendu', options: [{ v: '3d', label: 'Relief 3D' }, { v: '2d', label: 'Carte 2D' }], value: view, onChange: function (v) { view = v; T.store.set(K.view + ':' + kind, v); paint(); } }));
    box.appendChild(view === '2d' ? P.charts.heatmap2d({ surf: s }) : P.charts.surface3d({ surf: s }));
  }
  paint();
  var txt = { fins: 'Calculé, sans dérive : la probabilité que l’objectif soit touché avant le stop et avant la cloche, selon la largeur du stop (en écarts-types de la séance) et le rapport gain sur risque. Un grand rapport sur un stop large laisse la cloche décider.',
    delai: 'Calculé : le temps qu’il faut pour réunir 619 décisions (ALP nº 3, table 14) selon le nombre de contacts par semaine et la part qu’un signal garde. Hauteur en échelle logarithmique.',
    gros: 'Calculé, sans dérive : le nombre de trades qu’il faut pour avoir 90 % de chances de voir au moins un gain, selon le R:R et la largeur du stop. À 1:30 il en faut des dizaines ; à 1:500 sur un stop étroit, la séance ne porte presque jamais la cible. Hauteur en échelle logarithmique, plafonnée à 100 000.',
    liq: 'Le carnet dans le temps, en relief : la crête est le mur de liquidité. Quand il tient, la crête court jusqu’au bout ; apparu d’un coup, elle surgit juste avant le contact puis tombe ; retiré, elle tombe avant le contact ; mangé, elle s’érode pendant les frappes ; rechargé, elle redescend et remonte. Schéma, pas une donnée.',
    profil: 'Schéma : un profil de volume qui se construit au fil de la séance. Deux crêtes : les HVN, les prix où la séance a le plus échangé.' }[kind];
  var title = { fins: 'Les trois fins, en relief', delai: 'Le prix d’une confirmation', gros: 'Le prix d’un grand R:R', liq: 'Le mur, en relief', profil: 'Le profil, en relief' }[kind];
  return U.card({ title: title, meta: kind === 'liq' || kind === 'profil' ? 'schéma' : 'calculé', body: [h('p', { class: 'note', style: 'margin:0' }, txt), box] });
}
function openDesk(step, desk, tab) {
  T.nav.setReturn({ desk: 'plan', tab: 'carte', label: function () { return 'Revenir au plan · ' + step.short + ' ' + pctOf(step.id) + ' %'; }, onBack: function () { T.store.set(K.open, step.id); } });
  T.nav.go(desk, tab);
}
/* Un champ au gabarit du socle (div.fld.full > label, .in, .hint), pour un texte libre ou un sélecteur. */
function tfield(label, input, hint) { return h('div', { class: 'fld full' }, h('label', null, label), input.tagName === 'INPUT' ? h('div', { class: 'in' }, input) : input, hint || null); }
function hintEl(t) { return h('span', { class: 'hint' }, t || ''); }
function textInput(value, ph, onInput) {
  var el = h('input', { type: 'text', placeholder: ph, autocomplete: 'off', value: value || '' });
  el.addEventListener('input', function () { onInput(el.value); }); return el;
}
function put(patch) { var d = getDay(); Object.assign(d, patch); saveDay(d); return d; }
function zoneField(key, label, ph, refresh) {
  var info = hintEl(), paint = function () { var z = L.parseLevels(getDay()[key]); info.textContent = z.length ? z.length + ' zone' + (z.length > 1 ? 's' : '') + ' lue' + (z.length > 1 ? 's' : '') + ' : ' + z.map(function (x) { return x.lo === x.hi ? F.num(x.lo, 2) : F.num(x.lo, 2) + '–' + F.num(x.hi, 2); }).join(' · ') : 'Un bas et un haut par HVN ; une virgule suivie d’une espace sépare les HVN.'; };
  paint(); return tfield(label, textInput(getDay()[key], ph, function (v) { var o = {}; o[key] = v; put(o); paint(); refresh(); }), info);
}
function rrText(v) { return '1:' + F.num(v, v < 10 ? 1 : 0); }
/* Les champs d’un moment. reg(f) inscrit un repeint appelé quand un autre champ de l’étape change. */
L.INPUTS = ['annonces', 'fenetres', 'veille', 'dow', 'biais', 'gex', 'hvn', 'labo', 'prix', 'setups', 'sens', 'trig', 'stop', 'bruit', 'grandrr', 'taille'];
function inputNode(id, ctx, prefs, refresh, reg) {
  var day = getDay(), set = ctx.settings, box = h('div', { class: 'fields pl-flds' });
  if (id === 'annonces') {
    var info = hintEl(), pi = function () { var ev = events(getDay()), p = getPrefs(); info.textContent = ev.length ? ev.map(function (e) { return e.hhmm + ' ' + e.label + ' → pas d’ordre ' + L.minText(e.min - p.avant) + '–' + L.minText(e.min + p.apres); }).join(' · ') : 'Format : « 14:30 CPI, 16:00 ISM ». Heure de Paris.'; };
    pi(); reg(pi); box.appendChild(tfield('Annonces de rang 1', textInput(day.annonces, '14:30 CPI, 20:00 FOMC', function (v) { put({ annonces: v }); refresh(); }), info));
  } else if (id === 'fenetres') {
    box.appendChild(U.field({ label: 'Minutes avant', value: prefs.avant, unit: 'min', min: 0, max: 60, onChange: function (v) { var p = getPrefs(); p.avant = Math.round(v); savePrefs(p); refresh(); } }));
    box.appendChild(U.field({ label: 'Minutes après', value: prefs.apres, unit: 'min', min: 0, max: 120, onChange: function (v) { var p = getPrefs(); p.apres = Math.round(v); savePrefs(p); refresh(); } }));
  } else if (id === 'veille') {
    box.appendChild(tfield('La veille', U.seg({ aria: 'Tendance de la veille', value: day.veille, onChange: function (v) { writeBias(put({ veille: v })); ctx.rerender(); }, options: [{ v: 'hausse', label: 'Haussière' }, { v: 'range', label: 'Neutre' }, { v: 'baisse', label: 'Baissière' }] })));
  } else if (id === 'dow') {
    box.appendChild(tfield('Structure de Dow aujourd’hui', U.seg({ aria: 'Structure intraday', value: day.dow, onChange: function (v) { writeBias(put({ dow: v })); ctx.rerender(); }, options: [{ v: 'aligne', label: 'Alignée' }, { v: 'flou', label: 'Pas lisible' }, { v: 'casse', label: 'Cassée' }] })));
  } else if (id === 'biais' || id === 'sens') {
    var b = bias(day); box.appendChild(h('div', { style: 'grid-column:1/-1' }, U.callout([h('b', null, b ? 'Tendance ' + L.biasWord(b) + '. ' : 'Pas encore de tendance. '), L.sideRule(b).long])));
    if (id === 'biais') box.appendChild(tfield('Niveau qui annule la tendance', textInput(day.invalid, 'dernier creux ou sommet, ex. 31052', function (v) { put({ invalid: v }); })));
  } else if (id === 'gex') {
    var gx = gexLevels();
    box.appendChild(h('div', { style: 'grid-column:1/-1' }, gx.length ? U.callout([h('b', null, gx.length + ' niveau' + (gx.length > 1 ? 'x' : '') + ' gamma lu' + (gx.length > 1 ? 's' : '') + ' aujourd’hui. '), gx.map(function (g) { return g.label + ' ' + F.num(g.price, 2); }).join(' · ')]) : U.note('Aucun export GEX collé aujourd’hui dans NQ › GEX. Colle-le là-bas, ou note les niveaux à la main.')));
    if (!gx.length) box.appendChild(tfield('Niveaux gamma à la main', textInput(day.gexMan, 'CR 31400, PS 30900, HVL 31150', function (v) { put({ gexMan: v }); refresh(); })));
  } else if (id === 'hvn') box.appendChild(zoneField('hvn', 'HVN de la veille', '31080-31095, 31220-31240', refresh));
  else if (id === 'labo') box.appendChild(h('div', { style: 'grid-column:1/-1' }, U.button({ label: 'Enregistrer mes HVN pour le Labo', small: true, onClick: saveForLab })));
  else if (id === 'prix') {
    box.appendChild(U.field({ label: 'Prix du moment', value: day.prix, unit: 'pt', min: 1, max: 1e6, allowEmpty: true, onChange: function (v) { put({ prix: v > 0 ? v : null }); refresh(); } }));
    box.appendChild(U.field({ label: 'Distance d’une séance', value: prefs.range, unit: 'pt', min: 1, max: 1e5, allowEmpty: true, hint: 'du plus bas au plus haut, d’habitude', onChange: function (v) { var p = getPrefs(); p.range = v > 0 ? v : null; savePrefs(p); refresh(); } }));
    box.appendChild(U.field({ label: 'Marge derrière le HVN', value: prefs.marge, unit: 'ticks', min: 0, max: 80, onChange: function (v) { var p = getPrefs(); p.marge = Math.round(v); savePrefs(p); refresh(); } }));
    box.appendChild(U.field({ label: 'R:R minimal', value: prefs.rrMin, unit: '×', min: 0.5, max: 1000, hint: 'déclaré, modifiable', onChange: function (v) { var p = getPrefs(); p.rrMin = v; savePrefs(p); refresh(); } }));
  } else if (id === 'setups') {
    var tb = h('div', { style: 'grid-column:1/-1;min-width:0' }), ps = function () {
      var cr = dayCarte(getDay(), getPrefs()); T.clear(tb);
      tb.appendChild(cr.list.length ? U.table({ cols: [{ k: 'zone', label: 'Entrée', fmt: function (v, r) { return (r.side > 0 ? '▲ ' : '▼ ') + v.label + ' ' + F.num(r.entry, 2); } }, { k: 'stop', label: 'Stop', align: 'r', fmt: function (v) { return F.num(v, 2); } }, { k: 'label', label: 'Cible', fmt: function (v, r) { return v + ' ' + F.num(r.target, 2); } }, { k: 'rr', label: 'R:R', align: 'r', fmt: rrText }, { k: 'pObjectif', label: 'Atteinte', align: 'r', fmt: function (v, r) { return r.portee === false ? 'hors portée' : v == null ? '—' : F.pct(v, 1); } }], rows: cr.list.slice(0, 12), rowClass: function (r) { return r.rr >= getPrefs().rrMin && r.portee !== false ? null : 'neg'; } }) : U.note(bias(getDay()) === 'both' ? 'Tendance neutre : aucun setup.' : 'Aucun candidat : il faut la tendance, le prix, au moins un HVN du bon côté et un niveau gamma en face.'));
      tb.appendChild(U.note('Atteinte : probabilité que la cible soit touchée avant le stop et avant la fin de la séance, sans avantage, à la distance de séance saisie. Une ligne grisée ne passe pas ton R:R minimal ou sort de la portée.'));
    };
    ps(); reg(ps); box.appendChild(tb);
  } else if (id === 'trig') {
    box.appendChild(h('div', { style: 'grid-column:1/-1' }, U.callout([h('b', null, 'Trois lectures, trois trades. '), 'Absorption ou épuisement au contact : retournement dans le sens de la tendance. La zone cède dans le sens de la tendance : continuation. Aucune des trois : pas de trade.'])));
  } else if (id === 'stop') {
    box.appendChild(U.field({ label: 'Stop prévu (au-delà du mur + marge)', value: day.stop, unit: 'pt', min: 0.25, max: 500, allowEmpty: true, onChange: function (v) { put({ stop: v > 0 ? v : null }); refresh(); } }));
    box.appendChild(U.field({ label: 'Marge au-delà du mur', value: prefs.marge, unit: 'ticks', min: 0, max: 80, onChange: function (v) { var p = getPrefs(); p.marge = Math.round(v); savePrefs(p); refresh(); } }));
  } else if (id === 'bruit') {
    var nb = h('div', { style: 'grid-column:1/-1' }), pb = function () {
      var d = getDay(), p = getPrefs(), bm = L.bruitMinute(p.range); T.clear(nb);
      nb.appendChild(U.kpis([{ label: 'Bruit d’une minute', value: bm ? F.num(bm, 2) : '—', unit: 'pt', hint: p.range ? 'σ de séance ÷ √1 380' : 'saisis la distance d’une séance (étape Setup)' }, { label: 'Ton stop', value: d.stop ? F.num(d.stop, 2) : '—', unit: 'pt', hint: d.stop && bm ? F.num(d.stop / bm, 1) + ' fois le bruit' : 'étape Mur', tone: d.stop && bm && d.stop < 3 * bm ? 'neg' : null }, { label: 'Stop minimal', value: bm ? F.num(3 * bm, 2) : '—', unit: 'pt', hint: 'trois fois le bruit, déclaré' }], 3));
    };
    pb(); reg(pb); box.appendChild(nb);
  } else if (id === 'grandrr') {
    var gb = h('div', { style: 'grid-column:1/-1;min-width:0' }), pg = function () {
      var d = getDay(), p = getPrefs(), cost = set.commissionRT + 2 * set.tick * set.pointValue; T.clear(gb);
      if (!d.stop || !p.range) { gb.appendChild(U.note('Saisis ton stop (étape Mur) et la distance d’une séance (étape Setup) : le tableau se calcule avec tes nombres.')); return; }
      gb.appendChild(U.table({ cols: [{ k: 'rr', label: 'R:R', fmt: rrText }, { k: 'target', label: 'Cible', align: 'r', fmt: function (v) { return F.num(v, 1) + ' pt'; } }, { k: 'pSeance', label: 'Atteinte', align: 'r', fmt: function (v) { return v == null ? '—' : v < 1e-4 ? '< 0,01 %' : F.pct(v, 2); } }, { k: 'equilibre', label: 'Équilibre', align: 'r', fmt: function (v) { return F.pct(v, 2); } }, { k: 'n90', label: 'Trades pour 1 gain', align: 'r', fmt: function (v) { return v === Infinity ? 'jamais' : v == null ? '—' : F.int(Math.ceil(v)); } }, { k: 'portee', label: 'Cible / séance', align: 'r', fmt: function (v) { return v == null ? '—' : F.num(v, 1) + ' ×'; } }], rows: L.grandRR(d.stop, p.range, cost, set.pointValue), rowClass: function (r) { return r.portee > 1 ? 'neg' : null; } }));
      gb.appendChild(U.note('Sans avantage, à stop ' + F.num(d.stop, 2) + ' pt et séance de ' + F.num(p.range, 0) + ' pt. Atteinte : cible touchée avant le stop et avant la cloche. Équilibre : réussite qu’il faut juste pour payer ' + F.usd(cost, 2) + ' de coûts par aller-retour (commission et un tick de glissement par jambe). Trades pour 1 gain : nombre de trades pour avoir 90 % de chances d’en voir au moins un. Une cible plus grande que la séance (ligne grisée) n’est presque jamais atteinte avant la cloche (ALP nº 3, partie XXX). Un grand R:R ne crée aucun avantage : sans dérive, l’espérance reste égale aux coûts, au signe près.'));
    };
    pg(); reg(pg); box.appendChild(gb);
  } else if (id === 'taille') {
    var res = h('div', { style: 'grid-column:1/-1' }), pr = function () { var d = getDay(), st = L.todayStats(T.journal.list(), T.day.key()), n = L.contracts(set.riskPerTrade, d.stop, set.pointValue, set.commissionRT); T.clear(res); res.appendChild(U.kpis([{ label: 'Contrats', value: d.stop ? String(n) : '—', unit: set.instrument, hint: d.stop ? 'perte au stop ' + F.usd(n * (d.stop * set.pointValue + set.commissionRT), 0) : 'saisis le stop' }, { label: 'Trades', value: st.taken + ' / ' + set.maxTradesDay }, { label: 'Pertes', value: st.losses + ' / ' + set.maxLossesDay }], 3)); };
    pr(); reg(pr); box.appendChild(res);
  } else return null;
  return box;
}

/* Un moment de l’étape : VOIR (les planches), FAIRE (le champ), et sa case. */
function momentCard(step, it, i, ctx, prefs, onToggle, refresh, reg) {
  var day = getDay(), on = !!day.checks[step.id][i], card = h('div', { class: 'pl-mo' + (on ? ' on' : '') });
  var head = h('button', { class: 'pl-mh', type: 'button', role: 'checkbox', 'aria-checked': String(on) }, h('i', null, on ? '✓' : String(i + 1)), h('b', null, it.t), h('span', null, on ? 'fait' : 'à cocher'));
  head.addEventListener('click', function () { var nd = L.toggle(getDay(), step.id, i); saveDay(nd); syncPct(nd, step.id); var v = nd.checks[step.id][i]; card.classList.toggle('on', v); head.setAttribute('aria-checked', String(v)); head.firstChild.textContent = v ? '✓' : String(i + 1); head.lastChild.textContent = v ? 'fait' : 'à cocher'; onToggle(); });
  card.appendChild(head);
  card.appendChild(h('p', { class: 'pl-vf' }, h('span', { class: 'pl-tag' }, 'Voir'), it.voir));
  var figBox = h('div'), paintFigs = function () { T.clear(figBox); var c = carousel(it.figs || [], ctx, getDay(), getPrefs()); if (c) figBox.appendChild(c); };
  paintFigs(); card.appendChild(figBox);
  if ((it.figs || []).some(function (f) { return f.day || f.ladder || f.carte; })) reg(paintFigs);
  card.appendChild(h('p', { class: 'pl-vf' }, h('span', { class: 'pl-tag' }, 'Faire'), it.faire));
  if (it.principe) card.appendChild(U.prose([
    'Une information <b>publique et programmée</b> (CPI, emploi, FOMC) est dans le prix avant d’être publiée : le consensus l’est déjà. À l’heure dite, seul l’écart au consensus déplace le prix, en quelques secondes, et personne ne connaît son signe avant.',
    'Une information <b>privée</b>, ou une rumeur, entre lentement : ceux qui savent, ou croient savoir, se placent d’abord, et le prix dérive. Le jour où elle devient publique, il ne reste plus d’acheteur nouveau. <b>Achète la rumeur, vends l’annonce</b> : ceux qui ont acheté la rumeur vendent la nouvelle, même bonne.',
    'Principe de marché, non mesuré par ALP nº 3 : il dit quand ne pas trader, il ne donne aucun sens.']));
  if (it.input) { var n = inputNode(it.input, ctx, prefs, refresh, reg); if (n) card.appendChild(n); }
  if (it.desk) card.appendChild(U.button({ label: 'Ouvrir · ' + it.go + ' ›', small: true, kind: 'ghost', onClick: function () { openDesk(step, it.desk, it.tab); } }));
  return card;
}

function renderStep(root, ctx, step, day, prefs) {
  var idx = L.STEPS.indexOf(step), next = L.STEPS[idx + 1];
  function back() { T.store.set(K.open, null); ctx.rerender(); window.scrollTo(0, 0); }
  var tag = h('span', { class: 'pl-tag' });
  root.appendChild(h('div', { class: 'pl-head' }, h('button', { class: 'pl-back', type: 'button', on: { click: back } }, '‹ Carte'), tag));
  root.appendChild(U.page({ kicker: 'Plan · étape ' + step.n + ' / ' + L.STEPS.length, title: step.t.replace(/^(\S+)/, '*$1*'), lede: null }));
  root.appendChild(h('p', { class: 'pl-k5' }, step.k5));
  var regs = [], timer = 0, valid = h('div', { class: 'pl-valid' });
  var reg = function (f) { regs.push(f); };
  var refresh = function () { clearTimeout(timer); timer = setTimeout(function () { regs.forEach(function (f) { try { f(); } catch (e) {} }); }, 250); };
  var paintValid = function () {
    T.clear(valid); var pc = Math.max(L.ownPct(getDay(), step.id), pctOf(step.id)); tag.textContent = pc + ' %';
    valid.appendChild(U.button({ label: 'Valider à ' + pc + ' % et revenir à la carte', kind: 'acc', onClick: function () { syncPct(getDay(), step.id); T.toast(step.short + ' validé à ' + pctOf(step.id) + ' %'); back(); } }));
    if (next) valid.appendChild(U.button({ label: 'Étape suivante : ' + next.t + ' ›', kind: 'ghost', onClick: function () { syncPct(getDay(), step.id); T.store.set(K.open, next.id); ctx.rerender(); window.scrollTo(0, 0); } }));
  };
  var s1 = U.section('Le *déroulé*', step.items.length + ' moment' + (step.items.length > 1 ? 's' : '') + ', dans l’ordre');
  var list = h('div', { class: 'pl-mos' });
  step.items.forEach(function (it, i) { list.appendChild(momentCard(step, it, i, ctx, prefs, paintValid, refresh, reg)); });
  s1.appendChild(list); root.appendChild(s1);
  paintValid(); root.appendChild(valid);
}

/* Le mode Live : ce qu’il faut voir maintenant, pour la première case qui manque. */
L.ETATS = [['tient', 'Elle tient'], ['recharge', 'Se recharge'], ['epuisement', 'Épuisement'], ['continuation', 'Elle cède'], ['spawn', 'Mur apparu d’un coup'], ['retiree', 'Mur retiré']];
L.ETAT_OK = function (etat, b) { return etat === 'tient' || etat === 'recharge' || etat === 'epuisement' || (etat === 'continuation' && (b === 'long' || b === 'short')); };
function nowPanel(ctx, day, prefs, stt, fw, paint) {
  var b = bias(day), box = h('div', { class: 'pl-now' }), m = stt.miss, set = ctx.settings;
  var head = function (t, s) { box.appendChild(h('div', { class: 'pl-nowh' }, h('span', { class: 'pl-tag' }, stt.ok ? 'Feu vert' : 'Maintenant'), h('b', null, t), s ? h('span', null, s) : null)); };
  if (!m) {
    var n = L.contracts(set.riskPerTrade, day.stop, set.pointValue, set.commissionRT), cr = dayCarte(day, prefs);
    head('Tout est coché : l’ordre part.', (b === 'short' ? 'Vente' : 'Achat') + (day.stop ? ' · stop ' + F.num(day.stop, 2) + ' pt derrière le mur · ' + n + ' ' + set.instrument : ' · saisis le stop à l’étape Mur') + (cr.best ? ' · cible ' + cr.best.label + ' ' + F.num(cr.best.target, 2) : ''));
    box.appendChild(figCard({ carte: 1 }, ctx, day, prefs));
  } else if (m.id === 'fenetre') {
    head('Fenêtre interdite', fw.now ? fw.now.ev.label + ' ' + fw.now.ev.hhmm + ' : aucun ordre avant ' + L.minText(fw.now.until) + '.' : '');
    box.appendChild(figCard({ day: 1 }, ctx, day, prefs));
  } else if (m.id === 'zone') {
    head('Le prix est-il sur un de tes HVN ?', 'Du bon côté du prix, celui que la carte trace : sinon, rien à faire.');
    box.appendChild(figCard({ carte: 1 }, ctx, day, prefs)); box.appendChild(figCard({ s: 'zoneRebond' }, ctx, day, prefs));
  } else if (m.id === 'vwap') {
    head('La bande ' + (b === 'short' ? '+1,5σ ou +2,5σ' : b === 'long' ? '−1,5σ ou −2,5σ' : '±1,5σ') + ' est-elle touchée ?', L.sideRule(b).short + '.');
    box.appendChild(figCard({ v: b === 'short' ? 'vente' : 'achat' }, ctx, day, prefs));
  } else if (m.id === 'signal') {
    head('Que fait la zone au contact ?', 'Choisis ce que tu vois : la planche te dit quoi faire.');
    box.appendChild(U.chips({ options: L.ETATS.map(function (e) { return { v: e[0], label: e[1] }; }), value: day.live.etat, onChange: function (v) { var nd = getDay(); nd.live.etat = v; if (!L.ETAT_OK(v, b)) nd.live.signal = false; saveDay(nd); paint(); } }));
    var et = day.live.etat || (b === 'short' ? 'resistance' : 'tient');
    if (et === 'tient' && b === 'short') et = 'resistance';
    box.appendChild(figCard({ liq: et }, ctx, day, prefs));
  } else if (m.id === 'mur') {
    head('Un mur ancien, touché, qui tient ?', 'Présent depuis plusieurs minutes, des bulles dessus, il ne fond pas. Stop derrière lui.');
    box.appendChild(figCard({ liq: 'spawn' }, ctx, day, prefs)); box.appendChild(figCard({ s: 'risqueStop' }, ctx, day, prefs));
  } else if (m.id === 'risque') {
    var cr2 = dayCarte(day, prefs);
    head('La cible gamma tient-elle ton R:R ?', cr2.best ? cr2.best.label + ' ' + F.num(cr2.best.target, 2) + ' · R:R ' + rrText(cr2.best.rr) + '.' : 'La carte ne trouve aucun couple HVN–gamma qui passe ton R:R minimal.');
    box.appendChild(figCard({ carte: 1 }, ctx, day, prefs));
  }
  return box;
}
function renderLive(root, ctx, day, prefs) {
  var set = ctx.settings, b = bias(day);
  root.appendChild(summary(ctx, day, prefs));
  var s2 = U.section('Avant d’appuyer', 'dans l’ordre');
  var list = h('div', { class: 'pl-live' }), now = h('div'), verdict = h('div'), go = h('div', { class: 'pl-go' });
  var riskS = 'Cible le niveau gamma en face · R:R ≥ ' + F.num(prefs.rrMin, 1);
  function paint() {
    var d = getDay(), fw = fenetre(d, prefs), fOk = !fw.now, stt = L.liveState(d, fOk); T.clear(list); T.clear(verdict); T.clear(go); T.clear(now);
    L.LIVE.forEach(function (c) {
      var on = c.auto ? fOk : !!d.live[c.id], sub = c.auto ? (fw.now ? fw.now.ev.label + ' ' + fw.now.ev.hhmm + ' : attendre ' + L.minText(fw.now.until) : fw.next ? 'prochaine à ' + L.minText(fw.next.from) : events(d).length ? 'plus d’annonce' : 'aucune annonce saisie') : c.id === 'risque' ? riskS : c.id === 'vwap' ? L.sideRule(b).short : c.s;
      var cur = stt.miss && stt.miss.id === c.id;
      list.appendChild(h('button', { class: 'pl-lc' + (c.auto ? ' auto' : '') + (on ? '' : ' no') + (cur ? ' cur' : ''), type: 'button', role: 'checkbox', 'aria-checked': String(on), 'aria-disabled': c.auto ? 'true' : null, on: c.auto ? null : { click: function () { var nd = getDay(); nd.live[c.id] = !nd.live[c.id]; saveDay(nd); paint(); } } }, h('i', null, on ? '✓' : ''), h('b', null, c.t), h('span', null, sub)));
      if (cur) list.appendChild(nowPanel(ctx, d, prefs, stt, fw, paint));
    });
    if (stt.ok) now.appendChild(nowPanel(ctx, d, prefs, stt, fw, paint));
    verdict.appendChild(h('div', { class: 'pl-verdict' + (stt.ok ? ' ok' : '') }, h('b', null, stt.ok ? 'FEU VERT' : stt.n + ' / ' + L.LIVE.length), h('span', null, stt.ok ? 'Tout est coché. Le sens est celui de la tendance ; l’ordre part, le journal attendra.' : 'Manque : ' + stt.miss.t.toLowerCase() + '. Sans lui, c’est une passe.')));
    var take = function (side) { var at = Date.now(); T.journal.add(L.prisEntry(side, prefs, stt.ok, at, set.instrument, getDay().live.etat)); saveDay(L.resetLive(getDay())); T.toast((side === 'long' ? 'Achat' : 'Vente') + ' inscrit à ' + F.time(at) + ' : à compléter après'); paint(); };
    ['long', 'short'].forEach(function (side) {
      var ok = L.allowed(b, side), lab = side === 'long' ? '▲ J’achète' : '▼ Je vends';
      go.appendChild(U.button({ label: ok ? lab : lab + (b === 'both' ? ' · tendance neutre' : ' · contre la tendance'), kind: ok && stt.ok ? 'acc' : null, disabled: !ok, onClick: function () { take(side); } }));
    });
    var wide = U.button({ label: 'Je passe : inscrire le refus', kind: 'ghost', onClick: function () { var at = Date.now(), dd = getDay(), s2t = L.liveState(dd, !fenetre(dd, prefs).now); T.journal.add(L.refusEntry(s2t.miss, prefs, at, dd.live.etat)); saveDay(L.resetLive(getDay())); T.toast('Passe inscrite à ' + F.time(at)); paint(); } }); wide.classList.add('wide'); go.appendChild(wide);
  }
  paint();
  s2.appendChild(list); s2.appendChild(now); s2.appendChild(h('div', { style: 'height:10px' })); s2.appendChild(verdict); s2.appendChild(h('div', { style: 'height:10px' })); s2.appendChild(go);
  s2.appendChild(U.note('Sous la première case qui manque, la planche de ce qu’il faut voir maintenant. Un geste inscrit l’heure, le sens et ce que le flux montrait ; le reste se complète au journal après la séance. Une passe ne porte ni sens ni mise.'));
  root.appendChild(s2);
  var s1 = U.section('Ta *carte*', 'tes niveaux');
  s1.appendChild(figCard({ carte: 1 }, ctx, day, prefs));
  root.appendChild(s1);
}

/* Les HVN du jour vont au Labo, dans levels/items, au nom HVN1… : la stratégie se testera dessus. */
function saveForLab() {
  var lv = L.labLevels(getDay()), names = Object.keys(lv);
  if (!names.length) { T.toast('Aucun HVN lu'); return; }
  var DN = T.lib.donnees, key = DN && DN.sessionKey ? DN.sessionKey(Date.now()) : T.day.key(), month = String(key).slice(0, 7);
  var col = T.ucoll('levels/items'), doc = col.get(month) || { days: {} }, days = Object.assign({}, doc.days || {}), cur = days[key] || {};
  var levels = Object.assign({}, cur.levels || {});
  Object.keys(levels).forEach(function (n) { if (/^(HVN|HVZ|LVN|LVH)\d+$/.test(n)) delete levels[n]; });
  Object.assign(levels, lv);
  days[key] = Object.assign({}, cur, { levels: levels, scale: cur.scale || 'contrat', source: cur.source ? (/plan/.test(cur.source) ? cur.source : cur.source + ' + plan') : 'plan' });
  col.set(month, Object.assign({}, doc, { days: days }));
  T.toast(names.length + ' HVN enregistré' + (names.length > 1 ? 's' : '') + ' pour la séance ' + key);
}

function renderMap(root, ctx, day, prefs) {
  root.appendChild(summary(ctx, day, prefs));
  var firstOpen = L.STEPS.findIndex(function (s) { return pctOf(s.id) < 100; });
  var s = U.section('La carte *du jour*', 'touche une étape');
  s.appendChild(U.flow({ nodes: L.STEPS.map(function (st, i) {
    var p = pctOf(st.id);
    return { title: st.t, sub: T.DAY_STEPS[i] ? T.DAY_STEPS[i].s : '', pct: p, state: p >= 100 ? 'done' : i === firstOpen ? 'active' : 'todo', go: p + ' % ›', onClick: function () { T.store.set(K.open, st.id); ctx.rerender(); window.scrollTo(0, 0); } };
  }) }));
  s.appendChild(U.note('Chaque étape montre quoi voir et quoi faire, moment par moment, et se valide d’un bouton qui ramène ici. Le pourcentage suit les cases cochées ; un desk qui valide l’étape de son côté la porte à 100 %.'));
  root.appendChild(s);
  var s2 = U.section('Ta *carte*', 'le setup sur tes niveaux');
  s2.appendChild(figCard({ carte: 1 }, ctx, day, prefs));
  s2.appendChild(h('div', { style: 'margin-top:12px' }, U.button({ label: 'Passer en mode Live ›', onClick: function () { ctx.setTab('live'); } })));
  root.appendChild(s2);
}

/* La méthode : l’ordre retenu, ce qui manquait, et comment la tester. */
L.ORDRE = [
  { t: 'Macro et calendrier', s: 'D’abord ce qui interdit : une fenêtre interdite annule tout le reste.' },
  { t: 'Tendance : haussière, neutre ou baissière', s: 'Le sens avant les niveaux. Neutre : pas de trade.' },
  { t: 'Tracer les niveaux gamma', s: 'Ce sont les cibles, jamais les entrées.' },
  { t: 'Tracer les HVN', s: 'Seulement les nœuds de haut volume de la veille : ce sont les zones d’entrée.' },
  { t: 'Ta carte : y a-t-il un setup ?', s: 'Tendance, HVN et gamma sur une planche : entrée au bord du HVN, stop derrière, cible gamma, R:R calculé.' },
  { t: 'VWAP : contact de ±1,5σ ou ±2,5σ', s: 'Du côté que la tendance autorise.' },
  { t: 'Absorption, épuisement ou continuation', s: 'Le flux au contact dit quel trade existe.' },
  { t: 'Le mur et le stop', s: 'Un mur ancien, touché, qui tient ; le stop derrière lui.' },
  { t: 'Cible gamma et R:R', s: 'Un stop hors du bruit, une cible que la séance peut porter.' }
];
L.MANQUAIT = [
  { t: 'Un grand R:R se paie en fréquence', s: 'À 1:30 sans avantage, la cible tombe environ une fois sur trente et une ; à 1:500, une fois sur cinq cents, et seulement si la séance la porte. Il faut savoir combien de pertes d’affilée on accepte avant de commencer.' },
  { t: 'La portée de la séance', s: 'Une cible plus loin que ce qu’une séance parcourt n’arrive presque jamais avant la cloche (ALP nº 3, partie XXX). Le tableau de l’étape Cible le chiffre avec tes nombres.' },
  { t: 'Le bruit d’une minute', s: 'Un stop plus petit que lui est pris par le hasard. L’étape Cible le calcule.' },
  { t: 'Un mur qui vient d’apparaître', s: 'C’est la forme des ordres de manipulation sanctionnés sur le CME. Il ne protège pas un stop.' },
  { t: 'La continuation', s: 'Une zone qui cède dans le sens de la tendance est un trade ; contre la tendance, rien.' },
  { t: 'Le nombre de décisions', s: 'Il en faut 619 pour établir un Sharpe de 0,10 par trade ; avec un grand R:R, beaucoup plus, parce que les gains sont rares.' }
];
function renderMethode(root, ctx, prefs) {
  var s1 = U.section('L’ordre *retenu*', 'du plus large au plus fin');
  s1.appendChild(h('ol', { class: 'pl-ord' }, L.ORDRE.map(function (o) { return h('li', null, h('b', null, o.t), h('span', null, o.s)); })));
  s1.appendChild(U.note('Chaque étape élimine ce qui rendrait les suivantes inutiles. Le journal vient après la séance, jamais pendant. La stratégie de scalp est un autre plan : desk R&D.'));
  root.appendChild(s1);
  var s2 = U.section('Ce que la méthode *n’écrivait pas*', L.MANQUAIT.length + ' points');
  s2.appendChild(h('ol', { class: 'pl-ord' }, L.MANQUAIT.map(function (o) { return h('li', null, h('b', null, o.t), h('span', null, o.s)); })));
  root.appendChild(s2);
  var s3 = U.section('La *tester*', 'au Labo');
  s3.appendChild(U.prose([
    'Le gabarit « Plan HVN » du Labo écrit la méthode en règles : tendance de la veille (clôture au-dessus de l’ouverture), prix sous la bande VWAP, rejet du HVN noté le plus proche, stop au-delà avec ta marge, objectif sur le niveau suivant. Le miroir donne la vente.',
    'Pour qu’il ait des HVN à lire, chaque matin le bouton « Enregistrer mes HVN pour le Labo » de l’étape HVN les range dans la séance du jour. Le footprint et la heatmap ne sont pas dans les barres d’une minute : l’absorption et les murs se testent au journal.']));
  s3.appendChild(U.button({ label: 'Créer la stratégie au Labo ›', onClick: function () { var LB = T.lib.labo; if (LB && LB.ui && LB.ui.useTemplate) { try { LB.ui.useTemplate('plan-hvz'); } catch (e) { T.toast('Gabarit indisponible'); } } ctx.go('labo', 'concevoir'); } }));
  root.appendChild(s3);
  var s4 = U.section('Ce que le plan *ne promet pas*');
  s4.appendChild(U.note('Sans avantage, toute géométrie rend −c/L : ni un filtre ni un grand R:R ne déplacent l’espérance (ALP nº 3, parties III et X). Le plan sert à décider toujours de la même façon, à tenir le risque, et à tout inscrire, passes comprises. Seul le journal dira s’il y a quelque chose.'));
  root.appendChild(s4);
}

var TABS = [{ id: 'carte', label: 'Carte' }, { id: 'live', label: 'Live' }, { id: 'methode', label: 'Méthode' }];
T.desk({
  id: 'plan', label: 'Plan de trading', glyph: '▸', group: 'Desk', order: 1, tabs: TABS,
  render: function (root, ctx) {
    injectCss();
    var tab = TABS.some(function (t) { return t.id === ctx.tab; }) ? ctx.tab : 'carte', day = getDay(), prefs = getPrefs();
    var open = T.store.get(K.open, null), step = tab === 'carte' && open ? L.STEP[open] : null;
    if (step) renderStep(root, ctx, step, day, prefs);
    else {
      var w = T.day.get(), heads = { carte: ['Plan · Carte', 'Préparer, *puis* trader.', 'Onze étapes dans l’ordre. Chacune dit quoi préparer, montre ses situations et se valide d’un bouton qui ramène ici.'], live: ['Plan · Live', 'Le plan, *maintenant*.', 'Un écran : où j’en suis, six cases, deux boutons, et sous la case qui manque ce qu’il faut voir. Le journal se complète après.'], methode: ['Plan · Méthode', 'La méthode, *dans l’ordre*.', 'Ta stratégie, rangée du plus large au plus fin, avec ce qu’elle n’écrivait pas et la façon de la tester.'] }[tab];
      root.appendChild(U.page({ kicker: heads[0], title: heads[1], lede: heads[2] }));
      root.appendChild(U.tabs({ tabs: TABS, value: tab, onChange: function (t) { T.store.set(K.open, null); ctx.setTab(t); } }));
      if (tab === 'live') renderLive(root, ctx, day, prefs);
      else if (tab === 'methode') renderMethode(root, ctx, prefs);
      else renderMap(root, ctx, day, prefs);
      void w;
    }
    var un1 = T.day.on(function () { if (!root.contains(document.activeElement) || document.activeElement === document.body) { /* rien : la vue se repeint à la demande */ } });
    var un2 = T.journal.on(function () { if (tab === 'live' || (tab === 'carte' && !step)) ctx.rerender(); });
    var tick = setInterval(function () { if (tab === 'live' && document.visibilityState === 'visible' && !(document.activeElement && /INPUT|TEXTAREA/.test(document.activeElement.tagName))) ctx.rerender(); }, 60000);
    return function () { un1(); un2(); clearInterval(tick); };
  }
});
