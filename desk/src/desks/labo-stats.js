/* Labo de stratégie — grammaire, normalisation, hachage, lecture en français, statistiques et verdict
   (LABO.md §3.0, §3.8 et §5). Fonctions pures du fil principal : aucun DOM, aucun T.store, aucun réglage lu.
   Ce fichier n’enregistre aucun desk : il publie T.lib.laboStats. Le moteur (T.lib.laboEngine) et le desk
   Quant (T.lib.quant) ne sont lus qu’à l’appel, jamais au chargement. resolve, mirror et stats sont des
   enveloppes du moteur : il n’en existe qu’une implémentation. Aucun prix de marché n’est écrit ici. */
T.lib = T.lib || {};
var LS = T.lib.laboStats = {};

/* ================================================================================================
   0. Outils
   ================================================================================================ */
var NY = 'America/New_York', PAR = 'Europe/Paris', MIN = 60000, DAY = 86400000;
function isNum(x) { return typeof x === 'number' && x - x === 0; }
function own(o, k) { return o != null && Object.prototype.hasOwnProperty.call(o, k); }
function clone(x) { return x === undefined ? undefined : JSON.parse(JSON.stringify(x)); }
function isObj(x) { return !!x && typeof x === 'object' && !Array.isArray(x); }
function isRef(x) { return typeof x === 'string' && x.charAt(0) === '$'; }
function deepEq(a, b) { return canon(a) === canon(b); }
function LE() {
  var L = T.lib && T.lib.laboEngine;
  if (!L || typeof L.op !== 'function') throw new Error('Moteur du Labo absent : chargez labo-engine avant d’appeler laboStats.');
  return L;
}
function QT() {
  var Q = T.lib && T.lib.quant;
  if (!Q || typeof Q.dsr !== 'function') throw new Error('Desk Quant absent : chargez quant avant d’appeler laboStats.');
  return Q;
}
function pad2(n) { return (n < 10 ? '0' : '') + n; }
function getPath(o, k) { var ps = k.split('.'), x = o; for (var i = 0; i < ps.length; i++) { if (x == null || typeof x !== 'object') return undefined; x = x[ps[i]]; } return x; }
function setPath(o, k, v) { var ps = k.split('.'), x = o; for (var i = 0; i < ps.length - 1; i++) { if (!isObj(x[ps[i]])) x[ps[i]] = {}; x = x[ps[i]]; } x[ps[ps.length - 1]] = v; }
function mean(a) { var s = 0; for (var i = 0; i < a.length; i++) s += a[i]; return a.length ? s / a.length : NaN; }
function sdev(a) { if (a.length < 2) return NaN; var m = mean(a), s = 0; for (var i = 0; i < a.length; i++) s += (a[i] - m) * (a[i] - m); return Math.sqrt(s / (a.length - 1)); }

/* ================================================================================================
   1. Grammaire (§3.8) — registre unique : l’éditeur, normalize, describe et la documentation de Claude
      lisent tous ceci. Un argument : { k (clé, pointée pour un sous-objet), type, label, options [{v, label}],
      def (valeur que vaut l’absence : complétée par normalize), init (valeur de départ de l’éditeur),
      req (requis), omit (la valeur par défaut s’écrit par l’absence : retirée si égale), nullable, min, max,
      gt (borne stricte), unit, cls (classe exigée d’un opérande), single (un seul nom), free (fuseau libre) }.
      Types : int, num, time, timePair, enum, operand, names, bool, cond, conds, barsOrTime, days.
      Toute valeur int ou num peut s’écrire "$nom" (paramètre).
   ================================================================================================ */
function A(k, type, label, o) { var a = { k: k, type: type, label: label }; if (o) for (var x in o) if (own(o, x)) a[x] = o[x]; if (a.init === undefined && a.def !== undefined) a.init = a.def; return a; }
function opt(v, label) { return { v: v, label: label }; }
var TZ_OPTIONS = [opt(PAR, 'Paris'), opt(NY, 'New York'), opt('America/Chicago', 'Chicago'), opt('Europe/London', 'Londres'), opt('UTC', 'UTC')];
var CLOSE = { f: 'close' };
var LAG = function () { return A('lag', 'int', 'Décalage (barres en arrière)', { def: 0, omit: true, min: 0, max: 500, unit: 'barres' }); };
var TZA = function (label) { return A('tz', 'enum', label || 'Fuseau (vide : celui de la séance)', { options: TZ_OPTIONS, free: true, def: null, omit: true }); };
var CMP_OPTS = [opt('>', 'au-dessus de'), opt('<', 'au-dessous de'), opt('>=', 'au niveau ou au-dessus de'), opt('<=', 'au niveau ou au-dessous de')];
var UPDOWN = [opt('up', 'à la hausse'), opt('down', 'à la baisse')];
var FROM_OPTS = [opt('above', 'en venant d’au-dessus'), opt('below', 'en venant d’au-dessous')];
var NAME_HINTS = ['HVL', 'CR', 'PS', 'GW', 'MP', 'RM', 'R1', 'R2', 'S1', 'S2'];

var OPERANDS = [
  { f: 'close', label: 'Clôture', cls: 'niveau', group: 'prix', args: [LAG()] },
  { f: 'open', label: 'Ouverture', cls: 'niveau', group: 'prix', args: [LAG()] },
  { f: 'high', label: 'Plus haut de la barre', cls: 'niveau', group: 'prix', args: [LAG()] },
  { f: 'low', label: 'Plus bas de la barre', cls: 'niveau', group: 'prix', args: [LAG()] },
  { f: 'hl2', label: 'Milieu de la barre (H + B) / 2', cls: 'niveau', group: 'prix', args: [LAG()] },
  { f: 'hlc3', label: 'Prix typique (H + B + C) / 3', cls: 'niveau', group: 'prix', args: [LAG()] },
  { f: 'body', label: 'Corps de la barre (clôture − ouverture)', cls: 'ecart', group: 'prix', args: [LAG()] },
  { f: 'range', label: 'Amplitude de la barre (haut − bas)', cls: 'neutre', group: 'prix', args: [LAG()] },
  { f: 'volume', label: 'Volume', cls: 'neutre', group: 'volume', args: [LAG()] },
  { f: 'rvol', label: 'Volume relatif à la même minute', cls: 'neutre', group: 'volume', args: [A('n', 'int', 'Séances précédentes moyennées', { req: true, init: 20, min: 1, max: 250, unit: 'séances' })] },
  { f: 'vwap', label: 'VWAP de séance (± k σ)', cls: 'niveau', group: 'seance', args: [A('k', 'num', 'Écart à la VWAP, en σ (0 : la VWAP elle-même)', { def: 0, omit: true, min: -6, max: 6, unit: 'σ' })] },
  { f: 'sess', label: 'Séance en cours (haut, bas, ouverture)', cls: 'niveau', group: 'seance', args: [A('of', 'enum', 'Grandeur', { def: 'high', options: [opt('high', 'plus haut jusqu’ici'), opt('low', 'plus bas jusqu’ici'), opt('open', 'ouverture de la séance')] })] },
  { f: 'prev', label: 'Séance précédente', cls: 'niveau', group: 'seance', args: [A('of', 'enum', 'Grandeur', { def: 'close', options: [opt('open', 'ouverture'), opt('high', 'plus haut'), opt('low', 'plus bas'), opt('close', 'clôture')] }), A('n', 'int', 'Combien de séances en arrière', { def: 1, min: 1, max: 20, unit: 'séances' })] },
  { f: 'or', label: 'Range d’ouverture (entre deux heures)', cls: 'niveau', group: 'seance', args: [A('from', 'time', 'Début du range', { req: true, init: '09:30' }), A('to', 'time', 'Fin du range (exclue)', { req: true, init: '09:45' }), TZA(), A('of', 'enum', 'Grandeur', { def: 'high', options: [opt('high', 'haut'), opt('low', 'bas'), opt('mid', 'milieu'), opt('open', 'ouverture'), opt('close', 'clôture')] })] },
  { f: 'at', label: 'Prix d’une barre à heure fixe', cls: 'niveau', group: 'seance', args: [A('time', 'time', 'Heure de la barre', { req: true, init: '09:30' }), TZA(), A('of', 'enum', 'Grandeur', { def: 'close', options: [opt('open', 'ouverture'), opt('close', 'clôture')] })] },
  { f: 'sma', label: 'Moyenne simple', cls: 'of', group: 'moyennes', args: [A('n', 'int', 'Longueur', { req: true, init: 20, min: 1, max: 5000, unit: 'barres' }), A('of', 'operand', 'De quoi (vide : la clôture)', { def: CLOSE, omit: true })] },
  { f: 'ema', label: 'Moyenne exponentielle', cls: 'of', group: 'moyennes', args: [A('n', 'int', 'Longueur', { req: true, init: 20, min: 1, max: 5000, unit: 'barres' }), A('of', 'operand', 'De quoi (vide : la clôture)', { def: CLOSE, omit: true })] },
  { f: 'hh', label: 'Plus haut des n barres précédentes', cls: 'of', group: 'moyennes', args: [A('n', 'int', 'Barres (la barre courante exclue)', { req: true, init: 20, min: 1, max: 5000, unit: 'barres' }), A('of', 'operand', 'De quoi (vide : le plus haut)', { def: { f: 'high' }, omit: true })] },
  { f: 'll', label: 'Plus bas des n barres précédentes', cls: 'of', group: 'moyennes', args: [A('n', 'int', 'Barres (la barre courante exclue)', { req: true, init: 20, min: 1, max: 5000, unit: 'barres' }), A('of', 'operand', 'De quoi (vide : le plus bas)', { def: { f: 'low' }, omit: true })] },
  { f: 'sd', label: 'Écart-type sur n barres', cls: 'neutre', group: 'moyennes', args: [A('n', 'int', 'Longueur', { req: true, init: 20, min: 2, max: 5000, unit: 'barres' }), A('of', 'operand', 'De quoi (vide : la clôture)', { def: CLOSE, omit: true })] },
  { f: 'atr', label: 'ATR (moyenne de Wilder du vrai range)', cls: 'neutre', group: 'moyennes', args: [A('n', 'int', 'Longueur', { def: 14, min: 1, max: 500, unit: 'barres' }), LAG()] },
  { f: 'rsi', label: 'RSI (Wilder, borné 0–100)', cls: 'oscillateur', group: 'moyennes', args: [A('n', 'int', 'Longueur', { def: 14, min: 1, max: 500, unit: 'barres' }), LAG()] },
  { f: 'tf', label: 'Échelle de temps supérieure', cls: 'of', group: 'moyennes', args: [A('m', 'enum', 'Barres de', { req: true, init: 15, options: [opt(5, '5 minutes'), opt(15, '15 minutes'), opt(30, '30 minutes'), opt(60, '60 minutes')] }), A('of', 'operand', 'Grandeur calculée sur ces barres (vide : la clôture)', { def: CLOSE, omit: true })] },
  { f: 'level', label: 'Niveau nommé (GEX ou autre)', cls: 'niveau', group: 'niveaux', args: [A('name', 'names', 'Nom du niveau', { req: true, single: true, init: 'HVL', options: NAME_HINTS })] },
  { f: 'nearest', label: 'Niveau nommé le plus proche', cls: 'niveau', group: 'niveaux', args: [A('side', 'enum', 'Côté du prix', { req: true, init: 'above', options: [opt('above', 'au-dessus de la clôture'), opt('below', 'au-dessous de la clôture')] }), A('names', 'names', 'Parmi (vide : tous)', { def: null, omit: true, options: NAME_HINTS })] },
  { f: 'time', label: 'Heure (minutes depuis minuit)', cls: 'neutre', group: 'temps', args: [TZA()] },
  { f: 'dow', label: 'Jour de la semaine (1 = lundi)', cls: 'neutre', group: 'temps', args: [] },
  { f: 'sessmin', label: 'Minutes depuis l’ancre', cls: 'neutre', group: 'temps', args: [] },
  { f: 'dist', label: 'Écart entre deux opérandes', cls: 'ecart', group: 'calcul', args: [A('a', 'operand', 'De', { req: true, init: CLOSE }), A('b', 'operand', 'À', { req: true, init: { f: 'vwap' } }), A('unit', 'enum', 'Unité', { def: 'pts', options: [opt('pts', 'points'), opt('ticks', 'ticks'), opt('atr', 'ATR'), opt('sd', 'σ de VWAP')] }), A('n', 'int', 'Longueur de l’ATR (unité ATR seulement)', { def: 14, min: 1, max: 500, unit: 'barres' })] },
  { f: 'op', form: 'op', label: 'Calcul entre deux opérandes (+ − × ÷)', cls: 'calcule', group: 'calcul', args: [A('op', 'enum', 'Opération', { req: true, init: '+', options: [opt('+', '+'), opt('-', '−'), opt('*', '×'), opt('/', '÷')] }), A('a', 'operand', 'Premier', { req: true, init: CLOSE }), A('b', 'operand', 'Second', { req: true, init: 1 })] },
  { f: 'const', form: 'const', label: 'Nombre ou paramètre ("$nom")', cls: 'constante', group: 'calcul', args: [A('v', 'num', 'Valeur', { req: true, init: 0 })] }
];
var CONDITIONS = [
  { key: 'cmp', label: 'Comparaison', args: [A('cmp', 'enum', 'Sens', { req: true, init: '>', options: CMP_OPTS }), A('a', 'operand', 'Ceci', { req: true, init: CLOSE }), A('b', 'operand', 'Cela', { req: true, init: { f: 'vwap' } })] },
  { key: 'cross', label: 'Croisement', args: [A('cross', 'enum', 'Sens', { req: true, init: 'up', options: UPDOWN }), A('a', 'operand', 'Ceci', { req: true, init: CLOSE }), A('b', 'operand', 'Croise cela', { req: true, init: { f: 'vwap' } })] },
  { key: 'touch', label: 'Contact d’un niveau', args: [A('touch', 'operand', 'Niveau', { req: true, cls: 'niveau', init: { f: 'vwap' } }), A('from', 'enum', 'Venant de', { req: true, init: 'above', options: FROM_OPTS })] },
  { key: 'reject', label: 'Rejet d’un niveau (contact puis clôture revenue)', args: [A('reject', 'operand', 'Niveau', { req: true, cls: 'niveau', init: { f: 'vwap' } }), A('from', 'enum', 'Venant de', { req: true, init: 'above', options: FROM_OPTS })] },
  { key: 'break', label: 'Cassure d’un niveau en clôture', args: [A('break', 'operand', 'Niveau', { req: true, cls: 'niveau', init: { f: 'prev', of: 'high', n: 1 } }), A('dir', 'enum', 'Sens', { req: true, init: 'up', options: UPDOWN })] },
  { key: 'bar', label: 'Couleur de la barre', args: [A('bar', 'enum', 'Barre', { req: true, init: 'up', options: [opt('up', 'haussière'), opt('down', 'baissière')] })] },
  { key: 'time', label: 'Plage horaire', args: [A('time', 'timePair', 'De … à … (fin exclue)', { req: true, init: ['09:30', '10:30'] }), TZA()] },
  { key: 'news', label: 'Pas de publication économique proche', args: [A('news.impact', 'int', 'Impact minimal (1 à 3)', { def: 1, init: 2, min: 1, max: 3 }), A('news.before', 'int', 'Minutes avant', { def: 0, init: 15, min: 0, max: 1440, unit: 'min' }), A('news.after', 'int', 'Minutes après', { def: 0, init: 15, min: 0, max: 1440, unit: 'min' })] },
  { key: 'all', label: 'Toutes ces conditions', args: [A('all', 'conds', 'Conditions', { req: true, init: [] })] },
  { key: 'any', label: 'Au moins une de ces conditions', args: [A('any', 'conds', 'Conditions', { req: true, init: [] })] },
  { key: 'not', label: 'Négation', args: [A('not', 'cond', 'Condition niée', { req: true })] },
  { key: 'for', label: 'Vraie sur les n dernières barres', args: [A('for', 'int', 'Barres', { req: true, init: 3, min: 1, max: 1000 }), A('cond', 'cond', 'Condition', { req: true })] },
  { key: 'within', label: 'Vraie au moins une fois sur les n dernières barres', args: [A('within', 'int', 'Barres', { req: true, init: 5, min: 1, max: 1000 }), A('cond', 'cond', 'Condition', { req: true })] }
];
var ORDER_AT = function () { return A('at', 'operand', 'Niveau de l’ordre', { req: true, cls: 'niveau', init: { f: 'vwap' } }); };
var ENTRIES = [
  { type: 'market', label: 'Au marché', args: [] },
  { type: 'limit', label: 'À cours limité', args: [ORDER_AT(), A('offset', 'int', 'Décalage vers l’intérieur', { def: 0, omit: true, min: 0, max: 400, unit: 'ticks' }), A('valid', 'barsOrTime', 'Validité (barres, ou heure HH:MM)', { def: 1, min: 1, max: 1440 }), A('through', 'bool', 'Remplie seulement si le prix passe au travers', { def: false }), TZA('Fuseau de l’heure de validité')] },
  { type: 'stop', label: 'Ordre stop (sur cassure)', args: [ORDER_AT(), A('offset', 'int', 'Décalage vers l’extérieur', { def: 0, omit: true, min: 0, max: 400, unit: 'ticks' }), A('valid', 'barsOrTime', 'Validité (barres, ou heure HH:MM)', { def: 1, min: 1, max: 1440 }), TZA('Fuseau de l’heure de validité')] }
];
var BUFFER = function () { return A('buffer', 'int', 'Marge vers l’extérieur', { def: 0, omit: true, min: 0, max: 400, unit: 'ticks' }); };
var STOPS = [
  { type: 'pts', label: 'À distance fixe', args: [A('value', 'num', 'Distance', { req: true, gt: 0, init: 10, unit: 'points' }), BUFFER()] },
  { type: 'atr', label: 'En multiples d’ATR', args: [A('value', 'num', 'Multiple', { req: true, gt: 0, init: 1.5, unit: 'ATR' }), A('n', 'int', 'Longueur de l’ATR', { def: 14, min: 1, max: 500, unit: 'barres' }), BUFFER()] },
  { type: 'swing', label: 'Au-delà du dernier creux ou sommet', args: [A('n', 'int', 'Barres regardées (signal compris)', { req: true, init: 5, min: 1, max: 500, unit: 'barres' }), BUFFER()] },
  { type: 'level', label: 'Sur un niveau', args: [A('at', 'operand', 'Niveau', { req: true, cls: 'niveau', init: { f: 'vwap' } }), BUFFER()] }
];
var TARGETS = [
  { type: 'r', label: 'En multiples du risque (R)', args: [A('value', 'num', 'Multiple', { req: true, gt: 0, init: 2, unit: 'R' })] },
  { type: 'pts', label: 'À distance fixe', args: [A('value', 'num', 'Distance', { req: true, gt: 0, init: 20, unit: 'points' })] },
  { type: 'atr', label: 'En multiples d’ATR', args: [A('value', 'num', 'Multiple', { req: true, gt: 0, init: 2, unit: 'ATR' }), A('n', 'int', 'Longueur de l’ATR', { def: 14, min: 1, max: 500, unit: 'barres' })] },
  { type: 'level', label: 'Sur un niveau', args: [A('at', 'operand', 'Niveau', { req: true, cls: 'niveau', init: { f: 'vwap' } }), A('dynamic', 'bool', 'Relu à chaque barre (valeur de la barre précédente)', { def: false })] },
  { type: 'none', label: 'Aucun objectif', args: [] }
];
var MANAGE = {
  breakeven: { label: 'Break-even', args: [A('r', 'num', 'Gain qui déclenche le break-even', { def: 1, gt: 0, max: 50, unit: 'R' }), A('offset', 'int', 'Stop posé à l’entrée plus', { def: 0, omit: true, min: -400, max: 400, unit: 'ticks' })] },
  trail: { label: 'Stop suiveur', types: [opt('pts', 'en points'), opt('atr', 'en ATR'), opt('r', 'en R')], args: [A('type', 'enum', 'Distance', { def: 'pts', options: [opt('pts', 'en points'), opt('atr', 'en ATR'), opt('r', 'en R')] }), A('value', 'num', 'Distance au plus haut atteint', { req: true, gt: 0, init: 8 }), A('n', 'int', 'Longueur de l’ATR (distance en ATR seulement)', { def: 14, min: 1, max: 500, unit: 'barres' }), A('start', 'num', 'Actif à partir de', { def: 0, min: 0, max: 50, unit: 'R' })] },
  args: [A('maxBars', 'int', 'Sortie après n barres (entrée comprise)', { def: null, nullable: true, min: 1, max: 1440, unit: 'barres' }), A('exitOnOpposite', 'bool', 'Sortie sur signal opposé', { def: false })]
};
var RISK = [
  A('mode', 'enum', 'Taille', { def: 'contracts', options: [opt('contracts', 'quantité fixe'), opt('risk', 'calculée sur le risque en dollars')] }),
  A('contracts', 'int', 'Contrats par trade', { def: 1, min: 1, max: 1000 }),
  A('riskUsd', 'num', 'Risque par trade', { def: 150, gt: 0, max: 1e6, unit: '$' }),
  A('maxQty', 'int', 'Plafond de contrats (vide : aucun)', { def: null, nullable: true, min: 1, max: 1000 }),
  A('minStopTicks', 'int', 'Stop minimal (sinon trade annulé)', { def: 4, min: 0, max: 1000, unit: 'ticks' }),
  A('maxPerSession', 'int', 'Entrées par séance au plus (vide : sans limite)', { def: 3, nullable: true, min: 1, max: 1000 }),
  A('maxLossesPerSession', 'int', 'Pertes par séance au plus (vide : sans limite)', { def: 2, nullable: true, min: 1, max: 1000 }),
  A('dailyStopUsd', 'num', 'Perte nette de séance qui arrête tout (vide : aucune)', { def: 400, nullable: true, gt: 0, max: 1e7, unit: '$' }),
  A('cooldown', 'int', 'Barres sans signal après une sortie', { def: 0, min: 0, max: 1440, unit: 'barres' })
];
var COSTS = [
  A('commissionRT', 'num', 'Commission aller-retour par contrat (vide : celle des réglages, figée au scellement)', { def: null, nullable: true, min: 0, max: 1000, unit: '$' }),
  A('slipTicks', 'num', 'Glissement par jambe exécutée au marché ou au stop', { def: 1, min: 0, max: 100, unit: 'ticks' })
];
var SESSION = [
  A('tz', 'enum', 'Fuseau des heures', { def: PAR, options: TZ_OPTIONS, free: true }),
  A('from', 'time', 'Début de la fenêtre d’entrée', { def: '00:00' }),
  A('to', 'time', 'Fin de la fenêtre d’entrée (exclue)', { def: '09:00' }),
  A('flat', 'time', 'Sortie forcée (vide : fin de fenêtre)', { def: '09:00' }),
  A('days', 'days', 'Jours (date de la clé, 1 = lundi)', { def: [1, 2, 3, 4, 5] }),
  A('warmup', 'int', 'Amorçage après l’ancre (aucun signal avant)', { def: 15, min: 0, max: 1380, unit: 'min' })
];
LS.GRAMMAR = {
  classes: [opt('niveau', 'niveau (un prix)'), opt('ecart', 'écart (une différence de prix, en points)'), opt('oscillateur', 'oscillateur (borné de 0 à 100)'), opt('neutre', 'neutre (pas un prix)'), opt('constante', 'constante (un nombre ou un paramètre)')],
  groups: [opt('prix', 'Prix de la barre'), opt('volume', 'Volume'), opt('seance', 'Séance'), opt('moyennes', 'Moyennes et indicateurs'), opt('niveaux', 'Niveaux nommés'), opt('temps', 'Temps'), opt('calcul', 'Calculs')],
  operands: OPERANDS, conditions: CONDITIONS, entries: ENTRIES, stops: STOPS, targets: TARGETS,
  manage: MANAGE, risk: RISK, costs: COSTS, session: SESSION,
  anchors: [opt('globex', 'Globex : 18 h 00 New York, ouverture de la séance'), opt('paris', 'Paris : 00 h 00 heure de Paris'), opt('rth', 'Séance régulière : 09 h 30 New York (fenêtre dans 09 h 30–16 h 00)')],
  sides: [opt('long', 'Achat seulement'), opt('short', 'Vente seulement'), opt('both', 'Achat et vente')],
  fills: [opt('pessimiste', 'Pessimiste : le stop d’abord'), opt('optimiste', 'Optimiste : l’objectif d’abord (borne haute)'), opt('chemin', 'Chemin probable de la barre')],
  instruments: [opt('MNQ', 'Micro E-mini Nasdaq-100'), opt('NQ', 'E-mini Nasdaq-100')],
  /* Forme JSON de « op » : {op, a, b} ; de « const » : un nombre ou "$nom". Les autres : {f, …args}. */
  note: 'Chaque opérande est un objet {f, …} (calcul : {op, a, b} ; constante : nombre ou "$nom"). Chaque condition a une seule clé de forme (cmp, cross, touch, reject, break, bar, time, news, all, any, not, for, within).'
};
var OPMAP = {}, CONDMAP = {}, ENTMAP = {}, STOPMAP = {}, TGMAP = {};
OPERANDS.forEach(function (o) { OPMAP[o.f] = o; });
CONDITIONS.forEach(function (c) { CONDMAP[c.key] = c; });
ENTRIES.forEach(function (o) { ENTMAP[o.type] = o; });
STOPS.forEach(function (o) { STOPMAP[o.type] = o; });
TARGETS.forEach(function (o) { TGMAP[o.type] = o; });
var COND_KEYS = ['cmp', 'cross', 'touch', 'reject', 'break', 'bar', 'time', 'news', 'all', 'any', 'not', 'for', 'within'];
LS.COND_KEYS = COND_KEYS;

/* Valeurs par défaut (§3.0) : des constantes du code, jamais lues dans T.settings. */
LS.DEFAULTS = {
  instrument: 'MNQ', anchor: 'globex',
  session: { tz: PAR, from: '00:00', to: '09:00', flat: '09:00', days: [1, 2, 3, 4, 5], warmup: 15 },
  side: 'long', mirror: true, short: null, setup: [], entry: { type: 'market' },
  manage: { breakeven: null, trail: null, maxBars: null, exitOnOpposite: false },
  risk: { mode: 'contracts', contracts: 1, riskUsd: 150, maxQty: null, minStopTicks: 4, maxPerSession: 3, maxLossesPerSession: 2, dailyStopUsd: 400, cooldown: 0 },
  costs: { commissionRT: null, slipTicks: 1 }, fill: 'pessimiste', params: {}
};

/* ================================================================================================
   2. Classes des opérandes (§3.2) — codes du moteur : k constante, n niveau, e écart, o oscillateur, u neutre.
      Un test confronte ce typage au moteur (le miroir d’une comparaison à une constante révèle la classe).
   ================================================================================================ */
var CLS_NAME = { k: 'constante', n: 'niveau', e: 'ecart', o: 'oscillateur', u: 'neutre' };
var CLS_CODE = { niveau: 'n', ecart: 'e', oscillateur: 'o', neutre: 'u' };
function clsOf(x) {
  if (typeof x === 'number') return 'k';
  if (typeof x === 'string') { if (isRef(x)) return 'k'; throw new Error('Opérande inconnu : « ' + x + ' ».'); }
  if (!isObj(x)) throw new Error('Opérande invalide.');
  if (own(x, 'op')) {
    var a = clsOf(x.a), b = clsOf(x.b), op = x.op;
    if (a === 'o' || b === 'o') throw new Error('Opération sur un oscillateur refusée : comparez-le directement.');
    if (op === '+') {
      if (a === 'n' && b === 'n') throw new Error('Niveau + niveau refusé : une somme de prix n’est pas un prix.');
      if (a === 'n' || b === 'n') return 'n';
      if (a === 'e' && (b === 'e' || b === 'k')) return 'e';
      if (b === 'e' && a === 'k') return 'e';
      if (a === 'e' || b === 'e') throw new Error('Écart + neutre refusé.');
      return a === 'k' && b === 'k' ? 'k' : 'u';
    }
    if (op === '-') {
      if (a === 'n' && b === 'n') return 'e';
      if (a === 'n') return 'n';
      if (b === 'n') throw new Error('Soustraire un niveau d’un nombre est refusé.');
      if (a === 'e' && (b === 'e' || b === 'k')) return 'e';
      if (b === 'e' && a === 'k') return 'e';
      if (a === 'e' || b === 'e') throw new Error('Écart − neutre refusé.');
      return a === 'k' && b === 'k' ? 'k' : 'u';
    }
    if (op === '*' || op === '/') {
      if (a === 'n' || b === 'n') throw new Error('Niveau ' + (op === '*' ? '×' : '÷') + ' nombre refusé : le résultat n’est plus un prix.');
      if (a === 'e' && b === 'e') return 'u';
      if (a === 'e') return 'e';
      if (b === 'e') { if (op === '/') throw new Error('Nombre ÷ écart refusé.'); return 'e'; }
      return a === 'k' && b === 'k' ? 'k' : 'u';
    }
    throw new Error('Opération inconnue : « ' + op + ' ».');
  }
  var g = OPMAP[x.f];
  if (!g || g.form) throw new Error('Opérande inconnu : « ' + x.f + ' ».');
  if (g.cls === 'of') return clsOf(x.of == null ? (x.f === 'hh' ? { f: 'high' } : x.f === 'll' ? { f: 'low' } : CLOSE) : x.of);
  return CLS_CODE[g.cls];
}
/* Classe d’un opérande en toutes lettres : constante, niveau, ecart, oscillateur, neutre. Lève une erreur sur un
   typage refusé (niveau × nombre, niveau + niveau…). */
LS.classOf = function (x) { return CLS_NAME[clsOf(x)]; };

/* ================================================================================================
   3. Heures, fuseaux et ancres (§3.1). Une heure HH:MM d’un fuseau se lit en minutes depuis l’ancre
      (sessmin) : la prochaine occurrence à partir de l’ancre, comme le moteur. L’écart entre le fuseau de la
      stratégie et celui de l’ancre change pendant les semaines où les changements d’heure américain et
      européen sont décalés : on vérifie donc toutes les variantes d’une plage de trois ans (2025–2027).
   ================================================================================================ */
var DTFC = {}, TZOK = {};
function tzValid(tz) {
  if (typeof tz !== 'string' || !tz) return false;
  if (own(TZOK, tz)) return TZOK[tz];
  var ok = true; try { new Intl.DateTimeFormat('en-US', { timeZone: tz }).format(0); } catch (e) { ok = false; }
  TZOK[tz] = ok; return ok;
}
function offMin(tz, t) {
  if (tz === 'UTC') return 0;
  var f = DTFC[tz]; if (!f) f = DTFC[tz] = new Intl.DateTimeFormat('en-US', { timeZone: tz, hourCycle: 'h23', year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: 'numeric' });
  var o = {}, ps = f.formatToParts(new Date(t)); for (var i = 0; i < ps.length; i++) o[ps[i].type] = ps[i].value;
  var g = Date.UTC(+o.year, +o.month - 1, +o.day, (+o.hour) % 24, +o.minute), tm = Math.floor(t / MIN) * MIN;
  return Math.round((g - tm) / MIN);
}
function wallToUtc(g, tz) { var t = g - offMin(tz, g) * MIN; return g - offMin(tz, t) * MIN; }
function hmOf(s) { var m = /^(\d{1,2}):(\d{2})$/.exec(String(s)); return m ? +m[1] * 60 + +m[2] : NaN; }
function timeOk(s) { var m = /^(\d{1,2}):(\d{2})$/.exec(typeof s === 'string' ? s : ''); if (!m) return false; var h = +m[1], mi = +m[2]; return mi <= 59 && (h < 24 || (h === 24 && mi === 0)); }
function timeCanon(s) { var m = /^(\d{1,2}):(\d{2})$/.exec(s); return pad2(+m[1]) + ':' + m[2]; }
var ANCH = {
  globex: { tz: NY, min: 1080, prev: true },   /* 18:00 New York, la veille de la date de clé */
  paris: { tz: PAR, min: 0 },                   /* 00:00 Paris, la date de clé */
  rth: { tz: NY, min: 570, end: 390 }           /* 09:30 New York ; tout se tient dans 09:30–16:00 */
};
var VARC = {};
/* Variantes {w : minutes murales de l’ancre dans le fuseau tz, end : minutes de l’ancre à la fin de la séance
   Globex (17:00 New York)}, une par semaine (mercredi) de 2025 à 2027, dédoublonnées. */
function variants(anchor, tz) {
  var key = anchor + '|' + tz; if (VARC[key]) return VARC[key];
  var a = ANCH[anchor] || ANCH.globex, seen = {}, out = [], d0 = Date.UTC(2025, 0, 1);
  for (var wk = 0; wk < 157; wk++) {
    var day = d0 + wk * 7 * DAY, aDay = a.prev ? day - DAY : day;
    var tA = wallToUtc(aDay + a.min * MIN, a.tz), tE = wallToUtc(day + 1020 * MIN, NY);
    var wall = Math.round((((tA + offMin(tz, tA) * MIN) % DAY) + DAY) % DAY / MIN), end = a.end || Math.round((tE - tA) / MIN), k = wall + '|' + end;
    if (!seen[k]) { seen[k] = 1; out.push({ w: wall, end: end }); }
  }
  VARC[key] = out; return out;
}
function smOf(str, v) { var x = hmOf(str) - v.w; return x < 0 ? x + 1440 : x; }
function hText(s) { var m = /^(\d{1,2}):(\d{2})$/.exec(String(s)); return m ? pad2(+m[1]) + ' h ' + m[2] : String(s); }
function hmText(min) { min = ((min % 1440) + 1440) % 1440; return hText(pad2(Math.floor(min / 60)) + ':' + pad2(min % 60)); }
var TZ_TEXT = { 'Europe/Paris': 'heure de Paris', 'America/New_York': 'heure de New York', 'America/Chicago': 'heure de Chicago', 'Europe/London': 'heure de Londres', 'UTC': 'UTC' };
function tzText(tz) { return TZ_TEXT[tz] || ('fuseau ' + tz); }
LS.sessmins = function (anchor, tz, times) {
  return variants(anchor, tz).map(function (v) { var o = { anchorWall: v.w, sessionEnd: v.end }; (times || []).forEach(function (s) { o[s] = smOf(s, v); }); return o; });
};
var ANCHOR_TEXT = { globex: '18 h 00 New York', paris: '00 h 00 Paris', rth: '09 h 30 New York' };

/* ================================================================================================
   4. normalize(raw, ctx?) → { spec, errors, warnings } (§3.0 à §3.5, §2.2).
      ctx (facultatif) : { strict (identité exigée : id, sid), dataset (méta d’un jeu, ou { meta, adj, levels }
      tel que T.lib.donnees.loadDataset le rend), meta, adj, levels }. Les messages sont « chemin : phrase ».
   ================================================================================================ */
var TOP_KNOWN = ['id', 'sid', 'root', 'version', 'status', 'hash', 'sealedAt', 'createdAt', 'u', 'name', 'hypothesis', 'instrument', 'anchor', 'session', 'side', 'mirror', 'long', 'short', 'manage', 'risk', 'costs', 'fill', 'params'];
var TOP_QUIET = ['deleted', 'note', 'template', 'origin', 'tags'];
var SID_RE = /^s[a-z0-9]{6,20}$/, PNAME_RE = /^[A-Za-z_][A-Za-z0-9_]*$/;

LS.normalize = function (raw, ctx) {
  ctx = ctx || {};
  var E = [], W = [], P = {}, USED = {}, LEVELS = [], ORS = [];
  function err(p, m) { E.push((p ? p + ' : ' : '') + m); }
  function wrn(p, m) { W.push((p ? p + ' : ' : '') + m); }
  if (typeof raw === 'string') { try { raw = JSON.parse(raw); } catch (e) { return { spec: null, errors: ['JSON illisible : ' + e.message], warnings: [] }; } }
  if (!isObj(raw)) return { spec: null, errors: ['Une stratégie est un objet JSON.'], warnings: [] };

  /* ---- vérifications numériques (communes aux valeurs et aux paramètres) ---- */
  function numMsg(v, a) {
    if (!isNum(v)) return 'un nombre est attendu';
    if (a.type === 'int' || a.type === 'barsOrTime') { if (Math.floor(v) !== v) return 'un nombre entier est attendu'; }
    if (isNum(a.gt) && !(v > a.gt)) return 'doit être strictement supérieur à ' + fmtN(a.gt);
    if (isNum(a.min) && v < a.min) return 'doit valoir au moins ' + fmtN(a.min);
    if (isNum(a.max) && v > a.max) return 'doit valoir au plus ' + fmtN(a.max);
    return null;
  }
  function useParam(v, a, path) {
    var name = v.slice(1);
    if (!PNAME_RE.test(name)) { err(path, '« ' + v + ' » n’est pas un nom de paramètre valide.'); return undefined; }
    if (!own(P, name)) { err(path, '« ' + v + ' » : paramètre non déclaré (ajoutez-le dans params).'); return undefined; }
    USED[name] = true;
    var p = P[name], m = numMsg(p.v, a);
    if (m) err(path, 'paramètre « ' + name + ' » = ' + fmtN(p.v) + ' : ' + m + '.');
    ['min', 'max'].forEach(function (b) { if (isNum(p[b])) { var mb = numMsg(p[b], a); if (mb) wrn('params.' + name + '.' + b, 'hors de ce qu’accepte ' + path + ' (' + mb + ') : un balayage s’y arrêterait en erreur.'); } });
    return v;
  }
  /* ---- une valeur selon son argument ---- */
  function normVal(v, a, path) {
    if (v === undefined || v === null) {
      if (v === null && a.nullable) return null;
      if (a.req) { err(path, 'valeur requise (' + a.label.toLowerCase() + ').'); return undefined; }
      if (a.def === null) return a.omit ? undefined : (a.nullable ? null : undefined);
      if (a.def !== undefined && !a.omit) return clone(a.def);
      return undefined;
    }
    var r;
    switch (a.type) {
      case 'int': case 'num':
        if (isRef(v)) return useParam(v, a, path);
        r = numMsg(v, a); if (r) { err(path, r + ' (reçu ' + JSON.stringify(v) + ').'); return undefined; }
        r = v === 0 ? 0 : v; break;
      case 'barsOrTime':
        if (typeof v === 'string' && !isRef(v)) { if (!timeOk(v)) { err(path, 'nombre de barres ou heure HH:MM attendu (reçu « ' + v + ' »).'); return undefined; } r = timeCanon(v); break; }
        if (isRef(v)) return useParam(v, a, path);
        r = numMsg(v, a); if (r) { err(path, r + ' (reçu ' + JSON.stringify(v) + ').'); return undefined; }
        r = v; break;
      case 'time':
        if (!timeOk(v)) { err(path, 'heure HH:MM attendue (reçu ' + JSON.stringify(v) + ').'); return undefined; }
        r = timeCanon(v); break;
      case 'timePair':
        if (!Array.isArray(v) || v.length !== 2 || !timeOk(v[0]) || !timeOk(v[1])) { err(path, 'deux heures HH:MM attendues, par exemple ["09:30", "10:30"].'); return undefined; }
        r = [timeCanon(v[0]), timeCanon(v[1])]; break;
      case 'enum':
        if (a.free && a.k.slice(-2) === 'tz') { if (!tzValid(v)) { err(path, 'fuseau inconnu « ' + v + ' » (exemple : Europe/Paris).'); return undefined; } r = v; break; }
        if (!a.options.some(function (o) { return o.v === v; })) { err(path, 'valeur « ' + v + ' » inconnue ; attendu : ' + a.options.map(function (o) { return JSON.stringify(o.v); }).join(', ') + '.'); return undefined; }
        r = v; break;
      case 'bool':
        if (typeof v !== 'boolean') { err(path, 'true ou false attendu.'); return undefined; }
        r = v; break;
      case 'names':
        if (a.single) { if (typeof v !== 'string' || !v.trim()) { err(path, 'un nom de niveau attendu (texte).'); return undefined; } r = v.trim(); break; }
        if (typeof v === 'string') v = [v];
        if (!Array.isArray(v) || v.some(function (x) { return typeof x !== 'string' || !x.trim(); })) { err(path, 'une liste de noms de niveaux attendue.'); return undefined; }
        r = []; v.forEach(function (x) { x = x.trim(); if (r.indexOf(x) < 0) r.push(x); });
        if (!r.length) r = null;
        break;
      case 'days':
        if (!Array.isArray(v) || !v.length || v.some(function (d) { return !isNum(d) || Math.floor(d) !== d || d < 1 || d > 7; })) { err(path, 'liste de jours de 1 (lundi) à 7 (dimanche) attendue.'); return undefined; }
        r = []; v.forEach(function (d) { if (r.indexOf(d) < 0) r.push(d); }); r.sort(function (x, y) { return x - y; });
        if (r.some(function (d) { return d > 5; })) wrn(path, 'aucune séance Globex ne porte une clé de samedi ou de dimanche.');
        break;
      case 'operand':
        r = normOperand(v, path);
        if (r === undefined) return undefined;
        if (a.cls === 'niveau') {
          var c = safeCls(r, path);
          if (c === 'k') wrn(path, 'un prix fixe tient lieu de niveau : il ne vaut que pour la période où il a été lu.');
          else if (c && c !== 'n') { err(path, 'un niveau (un prix) est attendu ; reçu un opérande de classe ' + CLS_NAME[c] + '.'); return undefined; }
        }
        break;
      case 'cond': r = normCond(v, path); if (r === undefined) return undefined; break;
      case 'conds':
        if (!Array.isArray(v) || !v.length) { err(path, 'une liste non vide de conditions est attendue.'); return undefined; }
        r = []; for (var i = 0; i < v.length; i++) { var ci = normCond(v[i], path + '[' + i + ']'); if (ci !== undefined) r.push(ci); }
        break;
      default: err(path, 'type d’argument inconnu.'); return undefined;
    }
    if (a.omit && a.def !== undefined && deepEq(r, a.def)) return undefined;
    return r;
  }
  function normArgs(x, args, path, out, skip) {
    var used = {}; (skip || []).forEach(function (k) { used[k] = 1; });
    args.forEach(function (a) {
      used[a.k.split('.')[0]] = 1;
      var v = normVal(getPath(x, a.k), a, path + '.' + a.k);
      if (v !== undefined) setPath(out, a.k, v);
    });
    for (var k in x) if (own(x, k) && !used[k]) wrn(path, 'clé « ' + k + ' » inconnue, ignorée.');
    return out;
  }
  function safeCls(o, path) { try { return clsOf(o); } catch (e) { err(path, e.message); return null; } }
  function normOperand(x, path) {
    if (typeof x === 'number') { if (!isNum(x)) { err(path, 'nombre non fini.'); return undefined; } return x === 0 ? 0 : x; }
    if (typeof x === 'string') { if (isRef(x)) return useParam(x, { type: 'num' }, path); err(path, 'opérande inconnu « ' + x + ' » (un objet {f: …}, un nombre ou "$nom" est attendu).'); return undefined; }
    if (!isObj(x)) { err(path, 'opérande invalide.'); return undefined; }
    var o;
    if (own(x, 'op')) {
      o = normArgs(x, OPMAP.op.args, path, {});
      if (o.op === undefined || o.a === undefined || o.b === undefined) return undefined;
      if (safeCls(o, path) === null) return undefined;
      return o;
    }
    if (!own(x, 'f')) { err(path, 'opérande sans « f » ni « op ».'); return undefined; }
    var g = OPMAP[x.f];
    if (!g || g.form) { err(path, 'opérande inconnu « ' + x.f + ' ».'); return undefined; }
    o = normArgs(x, g.args, path, { f: x.f }, ['f']);
    if (x.f === 'dist') { if (o.unit !== 'atr') { if (x.n != null) wrn(path + '.n', 'sans effet hors de l’unité ATR, retiré.'); delete o.n; } else if (o.n === undefined) o.n = 14; }
    if (x.f === 'level' || x.f === 'nearest') LEVELS.push(path);
    if (x.f === 'or') ORS.push({ path: path, o: o });
    for (var i = 0; i < g.args.length; i++) if (g.args[i].req && o[g.args[i].k] === undefined) return undefined;
    if (safeCls(o, path) === null) return undefined;
    return o;
  }
  function normCond(c, path) {
    if (!isObj(c)) { err(path, 'condition invalide (un objet est attendu).'); return undefined; }
    var ks = COND_KEYS.filter(function (k) { return own(c, k); });
    if (!ks.length) { err(path, 'condition inconnue (clés : ' + Object.keys(c).join(', ') + ').'); return undefined; }
    if (ks.length > 1) { err(path, 'une seule forme par condition (trouvé : ' + ks.join(', ') + ') ; combinez-les par all ou any.'); return undefined; }
    if (ks[0] === 'news' && !isObj(c.news)) { err(path + '.news', 'un objet { impact, before, after } est attendu.'); return undefined; }
    var g = CONDMAP[ks[0]], o = normArgs(c, g.args, path, {});
    for (var i = 0; i < g.args.length; i++) if (g.args[i].req && getPath(o, g.args[i].k) === undefined) return undefined;
    return o;
  }
  function normOrder(x, map, path, what) {
    if (!isObj(x)) { err(path, what + ' : un objet {type, …} est attendu.'); return undefined; }
    var g = map[x.type];
    if (!g) { err(path, what + ' : type « ' + x.type + ' » inconnu ; attendu : ' + Object.keys(map).join(', ') + '.'); return undefined; }
    var o = normArgs(x, g.args, path, { type: x.type }, ['type']);
    for (var i = 0; i < g.args.length; i++) if (g.args[i].req && o[g.args[i].k] === undefined) return undefined;
    return o;
  }
  function normRule(r, path) {
    if (!isObj(r)) { err(path, 'règle invalide (un objet {setup, trigger, entry, stop, target} est attendu).'); return null; }
    var o = {}, setup = r.setup == null ? [] : Array.isArray(r.setup) ? r.setup : [r.setup];
    o.setup = [];
    setup.forEach(function (c, i) { var x = normCond(c, path + '.setup[' + i + ']'); if (x !== undefined) o.setup.push(x); });
    if (r.trigger == null) err(path + '.trigger', 'déclencheur requis.');
    else { var t = normCond(r.trigger, path + '.trigger'); if (t !== undefined) o.trigger = t; }
    o.entry = r.entry == null ? { type: 'market' } : normOrder(r.entry, ENTMAP, path + '.entry', 'entrée');
    if (r.stop == null) err(path + '.stop', 'stop requis.');
    else o.stop = normOrder(r.stop, STOPMAP, path + '.stop', 'stop');
    if (r.target == null) { wrn(path + '.target', 'objectif absent : aucun objectif retenu (la sortie viendra du stop, de la gestion ou de la fin de fenêtre).'); o.target = { type: 'none' }; }
    else o.target = normOrder(r.target, TGMAP, path + '.target', 'objectif');
    ['entry', 'stop', 'target'].forEach(function (k) { if (o[k] === undefined) delete o[k]; });
    for (var k in r) if (own(r, k) && ['setup', 'trigger', 'entry', 'stop', 'target'].indexOf(k) < 0) wrn(path, 'clé « ' + k + ' » inconnue, ignorée.');
    return o;
  }
  function normParams(x) {
    var out = {};
    if (x == null) return out;
    if (!isObj(x)) { err('params', 'un objet { nom: { v, min, max, step, label } } est attendu.'); return out; }
    Object.keys(x).forEach(function (name) {
      var p = x[name], path = 'params.' + name;
      if (!PNAME_RE.test(name)) { err(path, 'nom invalide (lettres, chiffres et _ ; commence par une lettre).'); return; }
      if (isNum(p)) p = { v: p };
      if (!isObj(p)) { err(path, 'un objet { v, min, max, step, label } est attendu.'); return; }
      if (!isNum(p.v)) { err(path + '.v', 'valeur numérique requise.'); return; }
      var o = { v: p.v === 0 ? 0 : p.v };
      ['min', 'max', 'step'].forEach(function (k) { if (p[k] == null) return; if (!isNum(p[k])) err(path + '.' + k, 'un nombre est attendu.'); else o[k] = p[k]; });
      if (isNum(o.min) && isNum(o.max) && o.min > o.max) err(path, 'min dépasse max.');
      if (isNum(o.min) && o.v < o.min) err(path + '.v', 'sous le minimum déclaré.');
      if (isNum(o.max) && o.v > o.max) err(path + '.v', 'au-dessus du maximum déclaré.');
      if (isNum(o.step) && !(o.step > 0)) err(path + '.step', 'le pas doit être positif.');
      if (p.label != null) { if (typeof p.label !== 'string') err(path + '.label', 'texte attendu.'); else o.label = p.label; }
      for (var k in p) if (own(p, k) && ['v', 'min', 'max', 'step', 'label'].indexOf(k) < 0) wrn(path, 'clé « ' + k + ' » inconnue, ignorée.');
      out[name] = o;
    });
    return out;
  }
  function normGroup(x, args, path) {
    if (x == null) x = {};
    if (!isObj(x)) { err(path, 'un objet est attendu.'); x = {}; }
    return normArgs(x, args, path, {});
  }
  function normManage(x) {
    var path = 'manage';
    if (x == null) x = {};
    if (!isObj(x)) { err(path, 'un objet est attendu.'); x = {}; }
    var o = { breakeven: null, trail: null };
    var be = x.breakeven;
    if (be != null && be !== false) {
      if (isNum(be) || isRef(be)) be = { r: be };
      if (!isObj(be)) err(path + '.breakeven', 'un nombre (en R) ou { r, offset } est attendu.');
      else o.breakeven = normArgs(be, MANAGE.breakeven.args, path + '.breakeven', {});
    }
    var tr = x.trail;
    if (tr != null && tr !== false) {
      if (!isObj(tr)) err(path + '.trail', 'un objet { type, value, n, start } est attendu.');
      else {
        tr = clone(tr);
        if (tr.value == null && tr.dist != null) { tr.value = tr.dist; delete tr.dist; }
        o.trail = normArgs(tr, MANAGE.trail.args, path + '.trail', {});
        if (o.trail.type !== 'atr') delete o.trail.n;
      }
    }
    normArgs(x, MANAGE.args, path, o, ['breakeven', 'trail']);
    return o;
  }

  /* ---- identité ---- */
  var s = raw, out = {}, strict = !!ctx.strict, ident = !ctx._rulesOnly;
  if (ident) {
    var hasSid = s.sid != null;
    if (hasSid && (typeof s.sid !== 'string' || !SID_RE.test(s.sid))) err('sid', 'identifiant invalide « ' + s.sid + ' » (s suivi de 6 à 20 lettres minuscules ou chiffres, sans _).');
    else if (!hasSid) (strict ? err : wrn)('sid', 'absent : la page en attribuera un à l’enregistrement.');
    var version = s.version == null ? 1 : s.version;
    if (!isNum(version) || version < 1 || Math.floor(version) !== version) { err('version', 'un entier ≥ 1 est attendu.'); version = 1; }
    if (s.id != null) { out.id = s.id; if (hasSid && s.id !== s.sid + '_v' + version) err('id', 'doit valoir sid + "_v" + version, soit « ' + s.sid + '_v' + version + ' ».'); }
    else if (hasSid) out.id = s.sid + '_v' + version;
    else if (strict) err('id', 'absent.');
    if (hasSid) out.sid = s.sid;
    if (s.root != null) { if (typeof s.root !== 'string' || !SID_RE.test(s.root)) err('root', 'identifiant d’origine invalide.'); out.root = s.root; }
    else if (hasSid) out.root = s.sid;
    out.version = version;
    out.status = s.status == null ? 'brouillon' : s.status;
    if (out.status !== 'brouillon' && out.status !== 'scellee') err('status', 'brouillon ou scellee attendu.');
    out.hash = s.hash == null ? null : s.hash;
    if (out.hash !== null && !/^h[0-9a-f]{16}$/.test(out.hash)) err('hash', 'format h + 16 chiffres hexadécimaux attendu.');
    if (out.status === 'scellee' && out.hash === null) err('hash', 'une version scellée porte son hachage.');
    out.sealedAt = s.sealedAt == null ? null : s.sealedAt;
    if (out.sealedAt !== null && !isNum(out.sealedAt)) err('sealedAt', 'instant en ms attendu.');
    if (out.status === 'scellee' && out.sealedAt === null) err('sealedAt', 'une version scellée porte sa date de scellement.');
    if (s.createdAt != null) out.createdAt = s.createdAt;
    if (s.u != null) out.u = s.u;
    out.name = typeof s.name === 'string' ? s.name : '';
    if (!out.name.trim()) wrn('name', 'stratégie sans nom.');
    out.hypothesis = typeof s.hypothesis === 'string' ? s.hypothesis : '';
    if (!out.hypothesis.trim()) wrn('hypothesis', 'hypothèse vide : elle est exigée pour sceller.');
  }
  /* ---- paramètres d’abord : les règles y renvoient ---- */
  P = normParams(s.params);
  var D = LS.DEFAULTS;
  out.instrument = s.instrument == null ? D.instrument : s.instrument;
  if (out.instrument !== 'MNQ' && out.instrument !== 'NQ') err('instrument', 'MNQ ou NQ attendu.');
  out.anchor = s.anchor == null ? D.anchor : s.anchor;
  if (!ANCH[out.anchor]) { err('anchor', 'globex, paris ou rth attendu.'); out.anchor = D.anchor; }
  var sx = s.session == null ? {} : s.session;
  if (isObj(sx) && sx.flat == null && sx.to != null) { sx = clone(sx); sx.flat = sx.to; }
  out.session = normGroup(sx, SESSION, 'session');
  if (out.session.tz === undefined) out.session.tz = D.session.tz;
  out.side = s.side == null ? D.side : s.side;
  if (['long', 'short', 'both'].indexOf(out.side) < 0) { err('side', 'long, short ou both attendu.'); out.side = 'long'; }
  out.mirror = s.mirror == null ? D.mirror : s.mirror;
  if (typeof out.mirror !== 'boolean') { err('mirror', 'true ou false attendu.'); out.mirror = true; }
  out.long = s.long == null ? null : normRule(s.long, 'long');
  out.short = s.short == null ? null : normRule(s.short, 'short');
  out.manage = normManage(s.manage);
  out.risk = normGroup(s.risk, RISK, 'risk');
  out.costs = normGroup(s.costs, COSTS, 'costs');
  out.fill = s.fill == null ? D.fill : s.fill;
  if (['pessimiste', 'optimiste', 'chemin'].indexOf(out.fill) < 0) { err('fill', 'pessimiste, optimiste ou chemin attendu' + (out.fill === 'vrai' ? ' (le remplissage vrai est réservé aux marches synthétiques et se choisit au lancement).' : '.')); out.fill = D.fill; }
  out.params = P;
  for (var k in s) if (own(s, k) && TOP_KNOWN.indexOf(k) < 0) { out[k] = clone(s[k]); if (TOP_QUIET.indexOf(k) < 0) wrn(k, 'clé inconnue, gardée telle quelle (elle n’entre pas dans le hachage).'); }

  /* ---- cohérence ---- */
  if (out.mirror && out.short) { wrn('short', 'ignoré : avec mirror = true, le côté vendeur est calculé par miroir.'); out.short = null; }
  if (!out.mirror && out.side !== 'long' && !out.short) err('short', 'obligatoire quand mirror vaut false et que la vente est jouée (side ' + out.side + ').');
  if (!out.long && !(out.side === 'short' && !out.mirror)) err('long', 'règle acheteuse requise' + (out.mirror ? ' : le miroir part du côté acheteur.' : '.'));
  if (out.risk.mode === 'risk' && out.risk.maxQty == null) wrn('risk.maxQty', 'aucun plafond de contrats : seul celui du compte bornera la taille.');
  windowChecks(out, err, wrn);
  ORS.forEach(function (x) { orChecks(out, x, err, wrn); });
  if (LEVELS.length) levelChecks(out, ctx, LEVELS, err, wrn);
  if (!E.length && out.long && out.mirror) {
    var needed = out.side !== 'long' || out.manage.exitOnOpposite === true;
    mirrorChecks(out, needed, needed ? err : wrn);
  }
  Object.keys(P).forEach(function (n) { if (!USED[n]) wrn('params.' + n, 'paramètre déclaré mais jamais utilisé.'); });
  return { spec: out, errors: E, warnings: W };
};
/* Fenêtre et sortie forcée : jamais à cheval sur l’ancre, et dans 09:30–16:00 pour rth (§3.1). */
function windowChecks(out, err, wrn) {
  var ses = out.session, tz = ses.tz;
  if (!tzValid(tz) || !timeOk(ses.from) || !timeOk(ses.to) || !timeOk(ses.flat)) return;
  var vs = variants(out.anchor, tz), straddle = 0, rth = 0, late = 0, empty = ses.from === ses.to;
  vs.forEach(function (v) {
    var f = smOf(ses.from, v), t = smOf(ses.to, v), fl = smOf(ses.flat, v);
    if (!(f < Math.min(t, fl))) straddle++;
    if (out.anchor === 'rth' && (f >= 390 || t > 390 || fl > 390)) rth++;
    if (f >= v.end) late++;
  });
  var win = hText(ses.from) + '–' + hText(ses.to) + ' (' + tzText(tz) + ')', walls = uniq(vs.map(function (v) { return hmText(v.w); }));
  if (empty) err('session', 'fenêtre vide : début et fin à ' + hText(ses.from) + '.');
  else if (straddle) err('session', 'la fenêtre ' + win + ' ou la sortie forcée de ' + hText(ses.flat) + ' chevauche l’ancre ' + out.anchor + ' (' + ANCHOR_TEXT[out.anchor] + ', soit ' + walls.join(' ou ') + ' ' + tzText(tz) + (vs.length > 1 ? ' selon les semaines' : '') + ') : elle commencerait après sa propre fin. Choisissez une fenêtre qui ne traverse pas l’ancre, ou un autre ancrage.');
  if (rth) err('session', 'ancrage rth : la fenêtre ' + win + ' et la sortie forcée doivent tenir dans 09 h 30–16 h 00 New York' + (rth < vs.length ? ' toutes les semaines (elles en sortent pendant les semaines de décalage d’heure)' : '') + '.');
  if (late && !straddle && !rth) wrn('session', 'la fenêtre commence après la fin de la séance Globex (17 h 00 New York)' + (late < vs.length ? ' certaines semaines' : '') + ' : aucune barre n’y tombe.');
  if (ses.warmup != null && isNum(ses.warmup) && !straddle && vs.every(function (v) { return smOf(ses.to, v) <= ses.warmup; })) wrn('session.warmup', 'l’amorçage couvre toute la fenêtre : aucun signal ne sera lu.');
}
function uniq(a) { var o = []; a.forEach(function (x) { if (o.indexOf(x) < 0) o.push(x); }); return o; }
/* Range d’ouverture : vide ou à cheval sur l’ancre → NaN toute la séance (§3.2). */
function orChecks(out, x, err, wrn) {
  var o = x.o, tz = o.tz || out.session.tz;
  if (!tzValid(tz) || !timeOk(o.from) || !timeOk(o.to)) return;
  var vs = variants(out.anchor, tz), bad = 0;
  vs.forEach(function (v) { if (!(smOf(o.from, v) < smOf(o.to, v))) bad++; });
  if (bad === vs.length) err(x.path, 'le range ' + hText(o.from) + '–' + hText(o.to) + ' (' + tzText(tz) + ') est vide ou commence avant l’ancre : il ne vaudrait jamais rien.');
  else if (bad) wrn(x.path, 'le range ' + hText(o.from) + '–' + hText(o.to) + ' (' + tzText(tz) + ') chevauche l’ancre certaines semaines : il sera indéfini ces séances-là.');
}
/* Niveaux nommés : jamais de NaN silencieux (§2.2). */
function levelChecks(out, ctx, paths, err, wrn) {
  var ds = ctx.dataset && isObj(ctx.dataset) && ctx.dataset.meta ? ctx.dataset : null;
  var meta = ctx.meta || (ds ? ds.meta : ctx.dataset) || null;
  var adj = ctx.adj !== undefined ? ctx.adj : ds ? ds.adj : undefined;
  var levels = ctx.levels !== undefined ? ctx.levels : ds ? ds.levels : undefined;
  var p = paths[0];
  if (!meta) { wrn(p, 'les niveaux nommés exigent un jeu dont le raccord des contrats est connu ; ce sera vérifié au lancement.'); return; }
  var name = meta.name ? '« ' + meta.name + ' »' : 'courant';
  if (meta.source === 'synthetique') { wrn(p, 'aucun niveau nommé n’existe sur une marche synthétique : la règle n’y déclenchera jamais.'); return; }
  if (meta.roll === 'ajuste') {
    var has = false; if (isObj(adj)) for (var k in adj) if (own(adj, k) && isNum(adj[k])) { has = true; break; }
    if (!has) err(p, 'le jeu ' + name + ' est ajusté mais ne porte pas ses ajustements par séance (adj) : un niveau publié en prix de contrat n’y tomberait pas au bon endroit.');
  } else if (meta.roll !== 'non-ajuste') err(p, 'le jeu ' + name + ' ne dit pas comment ses contrats sont raccordés (roll ' + (meta.roll || 'absent') + ') : un niveau nommé y tomberait à un prix faux. Précisez roll : ajuste (avec adj) ou non-ajuste.');
  if (isObj(levels)) {
    var bad = [];
    for (var key in levels) if (own(levels, key)) { var d = levels[key]; if (isObj(d) && isObj(d.levels) && d.scale === 'NDX' && !isNum(d.base)) bad.push(key); }
    if (bad.length) err(p, 'niveaux en échelle NDX sans base (NQ − NDX) pour ' + bad.length + ' séance' + (bad.length > 1 ? 's' : '') + ' (' + bad.slice(0, 3).join(', ') + (bad.length > 3 ? '…' : '') + ') : ils ne peuvent pas être portés sur le contrat.');
  }
}
/* Miroir (§3.4) : calculé par le moteur, après résolution, pièce par pièce pour nommer la pièce fautive. */
function mirrorChecks(out, needed, report) {
  var L = T.lib && T.lib.laboEngine, suf = needed ? '' : ' (sans effet tant que seul l’achat est joué)';
  if (!L || typeof L.mirror !== 'function') { report('long', 'moteur absent : le miroir n’a pas pu être vérifié.'); return; }
  var r;
  try { r = L.resolve(out, {}).long; } catch (e) { report('params', e.message); return; }
  (r.setup || []).forEach(function (c, i) { try { L.mirror(c, 'cond'); } catch (e) { report('long.setup[' + i + ']', e.message + suf); } });
  if (r.trigger) { try { L.mirror(r.trigger, 'cond'); } catch (e) { report('long.trigger', e.message + suf); } }
  var base = { setup: [], trigger: { bar: 'up' }, entry: { type: 'market' }, stop: { type: 'pts', value: 1 }, target: { type: 'none' } };
  ['entry', 'stop', 'target'].forEach(function (k) {
    if (!r[k]) return;
    var x = clone(base); x[k] = r[k];
    try { L.mirror(x, 'rule'); } catch (e) { report('long.' + k, e.message + suf); }
  });
}

/* ================================================================================================
   5. Enveloppes du moteur (une seule implémentation : laboEngine). Un test vérifie enveloppe = op.
   ================================================================================================ */
LS.resolve = function (spec, values) { return LE().resolve(spec, values); };
LS.mirror = function (x, kind, values) { return LE().mirror(x, kind, values); };
LS.stats = function (trades, pointValue) { return LE().stats(trades, pointValue); };

/* ================================================================================================
   6. Hachage (§5) : FNV-1a 64 bits exact sur les octets UTF-8 du JSON canonique de la spec normalisée puis
      résolue, sans params. Le hachage scellé couvre règles, session, anchor, side, mirror, manage, risk, costs
      (commissionRT figée) et fill ; configHash retire costs, fill, risk.contracts, risk.riskUsd, risk.maxQty.
   ================================================================================================ */
function canon(x) {
  if (x === null || x === undefined || typeof x === 'function') return 'null';
  if (typeof x === 'number') return x === 0 ? '0' : String(x);
  if (typeof x === 'string' || typeof x === 'boolean') return JSON.stringify(x);
  var s, i;
  if (Array.isArray(x)) { s = '['; for (i = 0; i < x.length; i++) s += (i ? ',' : '') + canon(x[i]); return s + ']'; }
  var ks = Object.keys(x).sort(), first = true; s = '{';
  for (i = 0; i < ks.length; i++) { var v = x[ks[i]]; if (v === undefined || typeof v === 'function') continue; s += (first ? '' : ',') + JSON.stringify(ks[i]) + ':' + canon(v); first = false; }
  return s + '}';
}
LS.canonical = canon;
function utf8(s) {
  var out = [], i, c, d, cp;
  for (i = 0; i < s.length; i++) {
    c = s.charCodeAt(i);
    if (c < 0x80) out.push(c);
    else if (c < 0x800) out.push(0xc0 | (c >> 6), 0x80 | (c & 63));
    else if (c >= 0xd800 && c < 0xdc00 && i + 1 < s.length && (d = s.charCodeAt(i + 1)) >= 0xdc00 && d < 0xe000) {
      cp = 0x10000 + ((c - 0xd800) << 10) + (d - 0xdc00); i++;
      out.push(0xf0 | (cp >> 18), 0x80 | ((cp >> 12) & 63), 0x80 | ((cp >> 6) & 63), 0x80 | (cp & 63));
    } else {
      if (c >= 0xd800 && c < 0xe000) c = 0xfffd;   /* demi-paire isolée : caractère de remplacement, comme TextEncoder */
      out.push(0xe0 | (c >> 12), 0x80 | ((c >> 6) & 63), 0x80 | (c & 63));
    }
  }
  return out;
}
LS.utf8 = utf8;
var BIG = null;
function fnvBig(bytes) {
  if (!BIG) BIG = { off: BigInt('0xcbf29ce484222325'), prime: BigInt('0x100000001b3'), mask: BigInt('0xffffffffffffffff') };
  var h = BIG.off;
  for (var i = 0; i < bytes.length; i++) { h = h ^ BigInt(bytes[i]); h = (h * BIG.prime) & BIG.mask; }
  var s = h.toString(16); while (s.length < 16) s = '0' + s;
  return s;
}
/* Même calcul en quatre membres de 16 bits, pour un moteur sans BigInt ; un test exige l’égalité. */
function fnvLimbs(bytes) {
  var h0 = 0x2325, h1 = 0x8422, h2 = 0x9ce4, h3 = 0xcbf2, p0 = 0x01b3, p2 = 0x0100, t, c;
  for (var i = 0; i < bytes.length; i++) {
    h0 ^= bytes[i];
    t = h0 * p0; var o0 = t % 65536; c = Math.floor(t / 65536);
    t = h1 * p0 + c; var o1 = t % 65536; c = Math.floor(t / 65536);
    t = h2 * p0 + h0 * p2 + c; var o2 = t % 65536; c = Math.floor(t / 65536);
    t = h3 * p0 + h1 * p2 + c; var o3 = t % 65536;
    h0 = o0; h1 = o1; h2 = o2; h3 = o3;
  }
  function hx(v) { var s = v.toString(16); while (s.length < 4) s = '0' + s; return s; }
  return hx(h3) + hx(h2) + hx(h1) + hx(h0);
}
LS.fnv64 = function (str, impl) { var b = utf8(String(str)); return impl === 'limbs' || (impl !== 'bigint' && typeof BigInt !== 'function') ? fnvLimbs(b) : fnvBig(b); };
var HASH_KEYS = ['anchor', 'session', 'side', 'mirror', 'long', 'short', 'manage', 'risk', 'costs', 'fill'];
function payload(spec, values, sealed, commissionRT) {
  var n = LS.normalize(spec, { _rulesOnly: true });
  if (n.errors.length) throw new Error('Hachage impossible : ' + n.errors[0]);
  var r = LE().resolve(n.spec, values || {}), o = {};
  HASH_KEYS.forEach(function (k) { o[k] = r[k] === undefined ? null : clone(r[k]); });
  if (sealed) { if (!isNum(o.costs.commissionRT)) o.costs.commissionRT = isNum(commissionRT) ? commissionRT : null; }
  else { delete o.costs; delete o.fill; delete o.risk.contracts; delete o.risk.riskUsd; delete o.risk.maxQty; }
  return o;
}
/* hash(spec, commissionRT?, values?) : hachage scellé. Une commission déclarée dans la spec l’emporte ; sinon
   commissionRT (la valeur du réglage au moment du scellement) ; sinon null. */
LS.hash = function (spec, commissionRT, values) { return 'h' + LS.fnv64(canon(payload(spec, values, true, commissionRT))); };
LS.configHash = function (spec, values) { return 'h' + LS.fnv64(canon(payload(spec, values, false))); };
LS.hashPayload = function (spec, o) { o = o || {}; return canon(payload(spec, o.values, o.kind !== 'config', o.commissionRT)); };
/* Sceller (§2.4 : seule la page scelle) : la commission du réglage est écrite dans costs, puis hachée. */
LS.seal = function (spec, commissionRT, at) {
  var n = LS.normalize(spec);
  if (n.errors.length) throw new Error('Scellement impossible : ' + n.errors[0]);
  if (!n.spec.hypothesis.trim()) throw new Error('Scellement impossible : écrivez d’abord l’hypothèse.');
  var s = clone(n.spec);
  if (!isNum(s.costs.commissionRT)) { if (!isNum(commissionRT)) throw new Error('Scellement impossible : commission du réglage inconnue.'); s.costs.commissionRT = commissionRT; }
  s.status = 'scellee'; s.sealedAt = isNum(at) ? at : Date.now(); s.hash = null;
  s.hash = LS.hash(s);
  return s;
};
LS.verifySeal = function (spec) {
  if (!spec || spec.status !== 'scellee') return { sealed: false, ok: false, hash: null };
  var h = null; try { h = LS.hash(spec); } catch (e) { return { sealed: true, ok: false, hash: null, why: e.message }; }
  return { sealed: true, ok: h === spec.hash, hash: h };
};

/* ================================================================================================
   7. Lecture en français (§5) : describe(spec, o?) → [{ id, title, text }], une phrase par bloc, côté
      vendeur reflété compris. o = { values, slipTicksRT (coût réalisé moyen, en ticks aller-retour) }.
   ================================================================================================ */
function fmtN(x) {
  if (!isNum(x)) return '—';
  var s = String(Math.abs(x)), dot = s.indexOf('.'), nd = dot < 0 || /e/.test(s) ? 0 : Math.min(4, s.length - dot - 1);
  if (T.fmt && T.fmt.num) return T.fmt.num(x, nd);
  return (x < 0 ? '−' : '') + Math.abs(x).toFixed(nd).replace('.', ',');
}
function fmtSigned(x) { return isNum(x) ? (x > 0 ? '+' : '') + fmtN(x) : '—'; }
function plural(n, one, many) { return isNum(n) && Math.abs(n) >= 2 ? many : one; }
function deX(s) { return /^le /.test(s) ? 'du ' + s.slice(3) : /^les /.test(s) ? 'des ' + s.slice(4) : 'de ' + s; }
function cap(s) { s = String(s); return s.charAt(0).toUpperCase() + s.slice(1); }
function lowFirst(s) { s = String(s); return /^.[a-zà-ÿ’ ]/.test(s) || s.length === 1 ? s.charAt(0).toLowerCase() + s.slice(1) : s; }
var DAYS = ['', 'lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche'];
function daysText(ds) {
  if (!Array.isArray(ds) || !ds.length) return 'aucun jour';
  var contiguous = ds.every(function (d, i) { return i === 0 || d === ds[i - 1] + 1; });
  if (ds.length >= 3 && contiguous) return 'du ' + DAYS[ds[0]] + ' au ' + DAYS[ds[ds.length - 1]];
  if (ds.length === 1) return 'le ' + DAYS[ds[0]] + ' seulement';
  return 'les ' + ds.slice(0, -1).map(function (d) { return DAYS[d]; }).join(', ') + ' et ' + DAYS[ds[ds.length - 1]];
}
function Reader(params) {
  var P = params || {};
  /* unit : un texte, ou [singulier, pluriel] choisi sur la valeur (celle du paramètre pour "$nom"). */
  function num(x, unit) {
    var ref = isRef(x), nm = ref ? x.slice(1) : '', p = ref ? P[nm] : null, v = ref ? (p && isNum(p.v) ? p.v : NaN) : x;
    var un = Array.isArray(unit) ? (isNum(v) ? plural(v, unit[0], unit[1]) : unit[1]) : unit, u = un ? ' ' + un : '';
    if (ref) return isNum(v) ? fmtN(v) + u + ' (paramètre ' + nm + ')' : 'le paramètre ' + nm + u;
    return isNum(x) ? fmtN(x) + u : 'une valeur non reconnue';
  }
  function lag(x) { var k = x.lag; return isRef(k) ? ' décalé de ' + num(k, ['barre', 'barres']) : k === 1 ? ' de la barre précédente' : isNum(k) && k > 1 ? ' d’il y a ' + fmtN(k) + ' barres' : ''; }
  function tzs(x) { return x && x.tz ? ' (' + tzText(x.tz) + ')' : ''; }
  var BASE = { close: 'la clôture', open: 'l’ouverture', high: 'le plus haut', low: 'le plus bas', hl2: 'le milieu de la barre', hlc3: 'le prix typique', volume: 'le volume', range: 'l’amplitude de la barre', body: 'le corps de la barre' };
  var SESS = { high: 'le plus haut de la séance jusqu’ici', low: 'le plus bas de la séance jusqu’ici', open: 'l’ouverture de la séance' };
  var PREV = { open: 'l’ouverture', high: 'le plus haut', low: 'le plus bas', close: 'la clôture' };
  var ORT = { high: 'le haut', low: 'le bas', mid: 'le milieu', open: 'l’ouverture', close: 'la clôture' };
  var UNIT = { pts: 'en points', ticks: 'en ticks', atr: 'en ATR', sd: 'en σ de VWAP' };
  var SYM = { '+': '+', '-': '−', '*': '×', '/': '÷' };
  function op(x) {
    if (typeof x === 'number' || isRef(x)) return num(x);
    if (!isObj(x)) return 'un opérande non reconnu';
    if (own(x, 'op')) {
      var c = null; try { c = clsOf(x); } catch (e) { c = null; }
      var pt = (c === 'n' || c === 'e') && (x.op === '+' || x.op === '-') ? 'points' : '';
      var a = typeof x.a === 'number' || isRef(x.a) ? num(x.a, pt) : op(x.a), b = typeof x.b === 'number' || isRef(x.b) ? num(x.b, pt) : op(x.b);
      return '(' + a + ' ' + (SYM[x.op] || x.op) + ' ' + b + ')';
    }
    var n = x.n, of;
    switch (x.f) {
      case 'close': case 'open': case 'high': case 'low': case 'hl2': case 'hlc3': case 'volume': case 'range': case 'body': return BASE[x.f] + lag(x);
      case 'vwap': return x.k == null || x.k === 0 ? 'la VWAP de séance' : isRef(x.k) ? 'la bande VWAP à ' + num(x.k, 'σ') : 'la bande VWAP à ' + fmtSigned(x.k) + ' σ';
      case 'sma': case 'ema': of = x.of == null ? 'la clôture' : op(x.of); return 'la moyenne ' + (x.f === 'sma' ? 'simple ' : 'exponentielle ') + deX(of) + ' sur ' + num(n, ['barre', 'barres']);
      case 'hh': return x.of == null ? 'le plus haut des ' + num(n, ['barre', 'barres']) + ' précédentes' : 'le maximum ' + deX(op(x.of)) + ' sur les ' + num(n, ['barre', 'barres']) + ' précédentes';
      case 'll': return x.of == null ? 'le plus bas des ' + num(n, ['barre', 'barres']) + ' précédentes' : 'le minimum ' + deX(op(x.of)) + ' sur les ' + num(n, ['barre', 'barres']) + ' précédentes';
      case 'sd': return 'l’écart-type ' + deX(x.of == null ? 'la clôture' : op(x.of)) + ' sur ' + num(n, ['barre', 'barres']);
      case 'atr': return 'l’ATR sur ' + num(n == null ? 14 : n, ['barre', 'barres']) + lag(x);
      case 'rsi': return 'le RSI sur ' + num(n == null ? 14 : n, ['barre', 'barres']) + lag(x);
      case 'rvol': return 'le volume relatif (rapporté à la même minute des ' + num(n, ['séance', 'séances']) + ' précédentes)';
      case 'prev': return (PREV[x.of || 'close'] || 'la clôture') + (x.n == null || x.n === 1 ? ' de la séance précédente' : ' de la séance d’il y a ' + num(x.n, ['séance', 'séances']));
      case 'sess': return SESS[x.of || 'high'] || SESS.high;
      case 'or': return (ORT[x.of || 'high'] || ORT.high) + ' du range ' + hText(x.from) + '–' + hText(x.to) + tzs(x);
      case 'at': return (x.of === 'open' ? 'l’ouverture' : 'la clôture') + ' de la barre de ' + hText(x.time) + tzs(x);
      case 'tf': return (x.of == null ? 'la clôture' : op(x.of)) + ' en barres de ' + num(x.m, ['minute', 'minutes']);
      case 'level': return 'le niveau ' + (x.name || 'nommé');
      case 'nearest': return 'le niveau nommé le plus proche ' + (x.side === 'below' ? 'au-dessous' : 'au-dessus') + ' de la clôture' + (Array.isArray(x.names) && x.names.length ? ' (parmi ' + x.names.join(', ') + ')' : '');
      case 'time': return 'l’heure' + tzs(x);
      case 'dow': return 'le jour de la semaine (1 = lundi)';
      case 'sessmin': return 'les minutes écoulées depuis l’ancre';
      case 'dist': return 'l’écart entre ' + op(x.a) + ' et ' + op(x.b) + ', ' + (x.unit === 'atr' ? 'en ATR sur ' + num(x.n == null ? 14 : x.n, ['barre', 'barres']) : UNIT[x.unit || 'pts'] || 'en points');
    }
    return 'un opérande non reconnu';
  }
  var CMPV = { '>': 'est au-dessus ', '<': 'est au-dessous ', '>=': 'est au niveau ou au-dessus ', '<=': 'est au niveau ou au-dessous ' };
  function cond(c) {
    if (!isObj(c)) return 'une condition non reconnue';
    if (own(c, 'cmp')) return op(c.a) + ' ' + (CMPV[c.cmp] || 'se compare ') + deX(op(c.b));
    if (own(c, 'cross')) return op(c.a) + ' croise ' + op(c.b) + (c.cross === 'down' ? ' à la baisse' : ' à la hausse');
    if (own(c, 'touch')) return c.from === 'below' ? 'le prix monte toucher ' + op(c.touch) + ' en venant d’au-dessous' : 'le prix redescend toucher ' + op(c.touch) + ' en venant d’au-dessus';
    if (own(c, 'reject')) return c.from === 'below' ? 'le prix monte toucher ' + op(c.reject) + ' puis clôture au-dessous (rejet)' : 'le prix redescend toucher ' + op(c.reject) + ' puis clôture au-dessus (rejet)';
    if (own(c, 'break')) return 'la clôture casse ' + op(c['break']) + (c.dir === 'down' ? ' à la baisse' : ' à la hausse');
    if (own(c, 'bar')) return c.bar === 'down' ? 'la barre est baissière (clôture sous l’ouverture)' : 'la barre est haussière (clôture au-dessus de l’ouverture)';
    if (own(c, 'time')) return Array.isArray(c.time) ? 'l’heure est entre ' + hText(c.time[0]) + ' et ' + hText(c.time[1]) + (c.tz ? ' (' + tzText(c.tz) + ')' : '') : 'une plage horaire non reconnue';
    if (own(c, 'news')) { var nw = isObj(c.news) ? c.news : {}; return 'aucune publication d’impact ' + num(nw.impact == null ? 1 : nw.impact) + ' ou plus entre ' + num(nw.before == null ? 0 : nw.before, 'min') + ' avant et ' + num(nw.after == null ? 0 : nw.after, 'min') + ' après'; }
    if (own(c, 'all')) return Array.isArray(c.all) && c.all.length ? c.all.map(cond).join(' et ') : 'une liste vide';
    if (own(c, 'any')) return Array.isArray(c.any) && c.any.length ? '(' + c.any.map(cond).join(', ou ') + ')' : 'une liste vide';
    if (own(c, 'not')) {
      var nt = c.not;
      if (isObj(nt) && own(nt, 'news')) { var nn = isObj(nt.news) ? nt.news : {}; return 'une publication d’impact ' + num(nn.impact == null ? 1 : nn.impact) + ' ou plus tombe entre ' + num(nn.before == null ? 0 : nn.before, 'min') + ' avant et ' + num(nn.after == null ? 0 : nn.after, 'min') + ' après'; }
      if (isObj(nt) && own(nt, 'bar')) return nt.bar === 'down' ? 'la barre n’est pas baissière' : 'la barre n’est pas haussière';
      return 'la condition « ' + cond(nt) + ' » est fausse';
    }
    if (own(c, 'for')) return cond(c.cond) + ', sur chacune des ' + num(c['for'], 'dernières barres');
    if (own(c, 'within')) return cond(c.cond) + ', au moins une fois sur les ' + num(c.within, 'dernières barres');
    return 'une condition non reconnue';
  }
  function bars(v) { return isRef(v) || isNum(v) ? num(v, ['barre', 'barres']) : 'jusqu’à ' + hText(v); }
  function entry(e, side) {
    e = e || { type: 'market' };
    var up = side > 0;
    if (e.type === 'limit' || e.type === 'stop') {
      var off = e.offset, inside = e.type === 'limit' ? (up ? 'sous' : 'au-dessus de') : (up ? 'au-dessus de' : 'sous');
      var at = op(e.at), where = off == null || off === 0 ? 'sur ' + at : num(off, ['tick', 'ticks']) + ' ' + (inside === 'sous' ? 'sous ' + at : 'au-dessus ' + deX(at));
      var valid = e.valid == null ? '1 barre' : typeof e.valid === 'string' && !isRef(e.valid) ? 'jusqu’à ' + hText(e.valid) + (e.tz ? ' (' + tzText(e.tz) + ')' : '') : bars(e.valid);
      if (e.type === 'limit') return 'à cours limité ' + where + ', valable ' + valid + ' ; ' + (e.through ? 'remplie seulement si le prix passe au travers' : 'remplie au contact') + ', sans glissement ; une limite déjà franchie à l’ouverture part au marché (marketable)';
      return 'par un ordre stop ' + where + ', valable ' + valid + ' ; rempli au pire de l’ouverture et du prix de l’ordre, glissement compris';
    }
    if (e.type === 'market') return 'au marché, à l’ouverture de la barre qui suit le signal ; le glissement joue contre soi';
    return 'par une entrée non reconnue';
  }
  function stop(s, side) {
    if (!isObj(s)) return 'un stop non reconnu';
    var below = side > 0 ? 'sous' : 'au-dessus de', buf = s.buffer;
    var marge = buf == null || buf === 0 ? '' : ', avec ' + num(buf, ['tick', 'ticks']) + ' de marge vers l’extérieur';
    switch (s.type) {
      case 'pts': return num(s.value, 'points') + ' ' + below + ' l’entrée' + marge;
      case 'atr': return num(s.value, 'ATR') + ' (ATR sur ' + num(s.n == null ? 14 : s.n, ['barre', 'barres']) + ', lu à la barre du signal) ' + below + ' l’entrée' + marge;
      case 'swing': return (side > 0 ? 'sous le plus bas' : 'au-dessus du plus haut') + ' des ' + num(s.n, 'dernières barres') + ' (barre du signal comprise)' + marge;
      case 'level': return 'sur ' + op(s.at) + ', lu à la barre du signal' + marge;
    }
    return 'un stop non reconnu';
  }
  function target(t, side) {
    if (!isObj(t)) return 'un objectif non reconnu';
    var beyond = side > 0 ? 'au-dessus de' : 'sous';
    switch (t.type) {
      case 'r': return num(t.value, 'R') + ' ' + beyond + ' l’entrée (en multiples de la distance du stop)';
      case 'pts': return num(t.value, 'points') + ' ' + beyond + ' l’entrée';
      case 'atr': return num(t.value, 'ATR') + ' (ATR sur ' + num(t.n == null ? 14 : t.n, ['barre', 'barres']) + ') ' + beyond + ' l’entrée';
      case 'level': return 'sur ' + op(t.at) + (t.dynamic ? ', relu à chaque barre (valeur de la barre précédente)' : ', figé à la barre du signal');
      case 'none': return 'aucun : la sortie vient du stop, de la gestion ou de la fin de fenêtre';
    }
    return 'un objectif non reconnu';
  }
  return { num: num, op: op, cond: cond, entry: entry, stop: stop, target: target };
}
LS.reader = function (params) { return Reader(params); };
var FILL_TEXT = {
  pessimiste: 'Remplissage pessimiste : quand une même barre touche le stop et l’objectif, le stop passe d’abord. C’est la lecture prudente des barres d’une minute.',
  optimiste: 'Remplissage optimiste : quand une même barre touche le stop et l’objectif, l’objectif passe d’abord. C’est une borne haute, jamais un résultat.',
  chemin: 'Remplissage par le chemin probable : une barre haussière se lit ouverture, bas, haut, clôture (le stop d’abord) ; une baissière, ouverture, haut, bas, clôture ; une barre sans corps prend le stop d’abord.'
};
LS.describe = function (spec, o) {
  o = o || {};
  var n = LS.normalize(spec), s = n.spec || LS.normalize({}).spec, out = [];
  var R = Reader(s.params), ses = s.session || {}, side = s.side || 'long', mirror = s.mirror !== false;
  function push(id, title, text) { text = String(text || '').trim(); if (!text) text = 'Non renseigné.'; if (!/[.!?»]$/.test(text)) text += '.'; out.push({ id: id, title: title, text: T.typo ? T.typo(cap(text)) : cap(text) }); }
  /* Séance et ancrage */
  var anc = { globex: 'les grandeurs de séance (VWAP, σ, range, heures) repartent de l’ouverture Globex, 18 h 00 New York', paris: 'les grandeurs de séance repartent de 00 h 00, heure de Paris', rth: 'les grandeurs de séance repartent de l’ouverture régulière, 09 h 30 New York, et n’existent qu’entre 09 h 30 et 16 h 00' }[s.anchor] || 'ancrage non reconnu';
  var flat = ses.flat && ses.flat !== ses.to ? ', sortie forcée à ' + hText(ses.flat) : ', sortie forcée en fin de fenêtre';
  push('seance', 'Séance et ancrage', 'Séance Globex ; ' + anc + '. Entrées entre ' + hText(ses.from) + ' et ' + hText(ses.to) + ' (' + tzText(ses.tz || PAR) + ')' + flat + ', ' + daysText(ses.days) + ' ; aucun signal pendant les ' + R.num(ses.warmup == null ? 0 : ses.warmup, ['minute', 'minutes']) + ' qui suivent l’ancre');
  /* Sens et miroir */
  var sens = side === 'long' ? 'Achat seulement' + (mirror ? ' ; le côté vendeur n’est pas joué' : '') : side === 'short' ? (mirror ? 'Vente seulement, jouée en miroir de la règle écrite à l’achat' : 'Vente seulement, sur la règle écrite côté vendeur') : (mirror ? 'Achat et vente. La vente est le miroir exact de l’achat : chaque prix p devient K − p, les comparaisons s’inversent, un écart change de signe, un oscillateur x devient 100 − x' : 'Achat et vente, chaque côté écrit séparément');
  push('sens', 'Sens et miroir', sens + '. Un signal d’achat et de vente sur la même barre ne donne aucun trade');
  /* Côté acheteur (ou règle source) */
  /* Règle source : celle de l’achat ; pour une vente seule écrite côté vendeur (mirror false), celle de la vente. */
  var L = s.long, ls = 1, srcNote = side === 'short' && mirror ? 'Règle écrite à l’achat, jouée seulement en miroir : ' : '';
  if (!L && side === 'short' && !mirror && s.short) { L = s.short; ls = -1; }
  var aS = ls > 0 ? 'à l’achat' : 'à la vente';
  if (L) {
    push('contexte', 'Contexte', L.setup && L.setup.length ? srcNote + aS + ', un signal n’est retenu que si ' + L.setup.map(R.cond).join(' et si ') : srcNote + 'aucun contexte : le déclencheur suffit');
    push('declencheur', 'Déclencheur', aS + ', le signal tombe à la clôture d’une barre où ' + (L.trigger ? R.cond(L.trigger) : 'rien n’est défini') + ' ; rien ne s’exécute avant la barre suivante');
    push('entree', 'Entrée', (ls > 0 ? 'Achat ' : 'Vente ') + R.entry(L.entry, ls));
    push('stop', 'Stop', 'Stop ' + R.stop(L.stop, ls) + ' ; un stop plus court que ' + R.num(s.risk && s.risk.minStopTicks != null ? s.risk.minStopTicks : 0, ['tick', 'ticks']) + ' annule le trade');
    push('objectif', 'Objectif', L.target && L.target.type === 'none' ? 'Aucun objectif : la sortie vient du stop, de la gestion ou de la fin de fenêtre' : 'Objectif ' + R.target(L.target, ls));
  } else push('declencheur', 'Déclencheur', side === 'short' && !mirror ? 'Aucune règle de vente n’est écrite' : 'Aucune règle d’achat n’est écrite');
  /* Côté vendeur, reflété compris */
  if (side !== 'long' && ls > 0) {
    var S = null, why = '', Rs = R;
    if (mirror) {
      try { S = LE().mirror(s, 'spec', o.values); Rs = Reader({}); } catch (e) { why = e.message; }
    } else S = s.short;
    if (S) {
      var parts = [];
      if (S.setup && S.setup.length) parts.push('un signal n’est retenu que si ' + S.setup.map(Rs.cond).join(' et si '));
      parts.push((parts.length ? 'il' : 'le signal') + ' tombe à la clôture d’une barre où ' + (S.trigger ? Rs.cond(S.trigger) : 'rien n’est défini'));
      parts.push('entrée ' + Rs.entry(S.entry, -1));
      parts.push('stop ' + Rs.stop(S.stop, -1));
      parts.push('objectif ' + Rs.target(S.target, -1));
      push('vendeur', 'Côté vendeur', 'À la vente' + (mirror ? ', en miroir de l’achat (paramètres résolus)' : '') + ' — ' + parts.join(' ; '));
    } else push('vendeur', 'Côté vendeur', mirror ? 'Miroir impossible : ' + (why || 'règle d’achat absente') : 'Aucune règle de vente n’est écrite');
  }
  /* Gestion */
  var M = s.manage || {}, g = [];
  if (M.breakeven) g.push('stop ramené à l’entrée' + (M.breakeven.offset ? ' ' + (isRef(M.breakeven.offset) || M.breakeven.offset > 0 ? 'plus ' : 'moins ') + R.num(isNum(M.breakeven.offset) ? Math.abs(M.breakeven.offset) : M.breakeven.offset, ['tick', 'ticks']) : '') + ' dès que le plus haut atteint +' + R.num(M.breakeven.r == null ? 1 : M.breakeven.r, 'R') + ' (le plus bas, à la vente)');
  if (M.trail) { var tt = M.trail, dist = tt.type === 'atr' ? R.num(tt.value, 'ATR') + ' (ATR sur ' + R.num(tt.n == null ? 14 : tt.n, ['barre', 'barres']) + ')' : tt.type === 'r' ? R.num(tt.value, 'R') : R.num(tt.value, 'points'); g.push('stop suiveur à ' + dist + ' du meilleur prix atteint depuis l’entrée' + (tt.start ? ', actif dès +' + R.num(tt.start, 'R') : '')); }
  if (M.maxBars != null) g.push('sortie à la clôture de la ' + R.num(M.maxBars) + 'e barre, entrée comprise');
  if (M.exitOnOpposite) g.push('sortie à l’ouverture suivante sur un signal opposé');
  push('gestion', 'Gestion', g.length ? 'Position suivie barre par barre : ' + g.join(' ; ') + '. Les mises à jour valent pour la barre suivante, jamais pour la courante' : 'Aucune gestion : le stop et l’objectif restent où ils ont été posés');
  /* Risque */
  var K = s.risk || {}, rk = K.mode === 'risk' ? 'Taille calculée pour risquer ' + R.num(K.riskUsd, '$') + ' par trade, stop et commission compris' + (K.maxQty != null ? ', au plus ' + R.num(K.maxQty, ['contrat', 'contrats']) : '') + ' (plafond du compte en plus)' : R.num(K.contracts == null ? 1 : K.contracts, ['contrat', 'contrats']) + ' par trade';
  var lim = [];
  if (K.maxPerSession != null) lim.push('au plus ' + R.num(K.maxPerSession, ['entrée', 'entrées']));
  if (K.maxLossesPerSession != null) lim.push(R.num(K.maxLossesPerSession, ['perte', 'pertes']) + ' au plus');
  if (K.dailyStopUsd != null) lim.push('plus d’entrée après ' + R.num(K.dailyStopUsd, '$') + ' de perte nette');
  var cd = K.cooldown == null || K.cooldown === 0 ? 'la barre de sortie peut porter un nouveau signal' : K.cooldown === 1 ? 'aucun signal sur la barre de sortie' : 'aucun signal pendant ' + R.num(K.cooldown, ['barre', 'barres']) + ' à partir de la barre de sortie, celle-ci comprise';
  push('risque', 'Risque', rk + '. Une position à la fois ; par séance, ' + (lim.length ? lim.join(', ') : 'aucune limite') + ' ; ' + cd);
  /* Coûts et convention de glissement */
  var C = s.costs || {}, com = C.commissionRT == null ? 'Commission : celle de tes réglages, figée dans le hachage au scellement' : 'Commission : ' + R.num(C.commissionRT, '$') + ' aller-retour par contrat';
  var sl = C.slipTicks == null ? 0 : C.slipTicks, rt = isRef(sl) ? null : 2 * sl;
  var slipText = 'Glissement : ' + R.num(sl, ['tick', 'ticks']) + ' par jambe exécutée au marché ou au stop (entrée au marché, stop ou marketable ; sorties au stop, break-even, suiveur, temps, sortie forcée, cloche ou signal opposé), jamais sur une limite ni sur l’objectif. Le desk Quant compte son glissement par aller-retour : ici, une entrée au marché sortie au stop paie ' + (rt === null ? 'deux fois ce glissement' : R.num(rt, ['tick', 'ticks'])) + ', une limite sortie à l’objectif n’en paie aucun';
  if (isNum(o.slipTicksRT)) slipText += ' ; coût réalisé moyen : ' + fmtN(Math.round(o.slipTicksRT * 100) / 100) + ' ' + plural(o.slipTicksRT, 'tick', 'ticks') + ' par aller-retour';
  push('couts', 'Coûts et glissement', com + '. ' + slipText);
  /* Remplissage */
  push('remplissage', 'Remplissage', FILL_TEXT[s.fill] || FILL_TEXT.pessimiste);
  /* Paramètres */
  var pn = Object.keys(s.params || {});
  if (pn.length) push('parametres', 'Paramètres', 'Paramètres : ' + pn.map(function (k) { var p = s.params[k]; return k + ' = ' + fmtN(p.v) + (p.label ? ', ' + lowFirst(p.label) : '') + (isNum(p.min) && isNum(p.max) ? ', balayable de ' + fmtN(p.min) + ' à ' + fmtN(p.max) + (isNum(p.step) ? ' par pas de ' + fmtN(p.step) : '') : ''); }).join(' ; '));
  return out;
};

/* ================================================================================================
   8. Statistiques : DSR, essais, PBO, plateau, stabilité, SPRT, CUSUM (§5).
   ================================================================================================ */
/* Sharpe déflaté (Bailey et López de Prado) par T.lib.quant.dsr ; sdTrials absent → 1/√n. */
LS.dsr = function (o) {
  o = o || {};
  var n = o.n, sd = isNum(o.sdTrials) && o.sdTrials > 0 ? o.sdTrials : null, r = QT().dsr(o.sr, n, o.N, o.skew, o.exkurt, sd);
  return { dsr: r.dsr, sr0: r.sr0, sr: o.sr, n: n, N: o.N, sdTrials: sd === null ? 1 / Math.sqrt(Math.max(n || 0, 1)) : sd, sdSource: sd === null ? 'defaut' : 'registre' };
};
function overlaps(a0, a1, b0, b1) { return !((b0 != null && a1 != null && a1 < b0) || (b1 != null && a0 != null && a0 > b1)); }
function essaisFor(rows, instrument, from, to) {
  return (rows || []).filter(function (r) { return r && Array.isArray(r.hashes) && (instrument == null || r.instrument === instrument) && overlaps(r.from, r.to, from, to); })
    .sort(function (a, b) { return (a.at || 0) - (b.at || 0) || String(a.id).localeCompare(String(b.id)); });
}
/* trials(essais, instrument, from, to, o?) → { N, sdTrials, inherited, docs, srs, sdSource }.
   N = configHash distincts des essais de même instrument dont [from, to] recoupe la période — toutes stratégies,
   versions et jeux confondus (§2.5). sdTrials = écart-type des Sharpe (un par configHash, le premier vu) s’il y
   en a au moins dix, sinon 1/√n quand o.n (trades du run évalué) est donné, null sinon (le DSR prend alors 1/√n). inherited = configHash dont le premier essai précède
   la migration (o.migratedAt en ms, ou o.lignee = document T.store labo:lignee). */
LS.trials = function (rows, instrument, from, to, o) {
  o = o || {};
  var mig = o.migratedAt, lg = o.lignee && (o.lignee.v || o.lignee);
  if (!isNum(mig) && lg && lg.migreLe != null) mig = isNum(lg.migreLe) ? lg.migreLe : Date.parse(lg.migreLe);
  var seen = {}, srs = [], N = 0, inh = 0, list = essaisFor(rows, instrument, from, to);
  list.forEach(function (r) {
    r.hashes.forEach(function (h, i) {
      if (typeof h !== 'string' || own(seen, h)) return;
      seen[h] = 1; N++;
      var sr = Array.isArray(r.sr) ? r.sr[i] : NaN; if (isNum(sr)) srs.push(sr);
      if (isNum(mig) && isNum(r.at) && r.at < mig) inh++;
    });
  });
  var sd = srs.length >= 10 ? sdev(srs) : isNum(o.n) && o.n > 0 ? 1 / Math.sqrt(o.n) : null;
  return { N: N, sdTrials: sd, sdSource: srs.length >= 10 ? 'registre' : 'defaut', inherited: inh, docs: list.length, srs: srs.length };
};
/* Les configHash d’un lancement jamais vus sur l’instrument et la période (ceux qui créent un essai). */
LS.newHashes = function (rows, instrument, from, to, hashes) {
  var seen = {}; essaisFor(rows, instrument, from, to).forEach(function (r) { r.hashes.forEach(function (h) { seen[h] = 1; }); });
  var out = []; (hashes || []).forEach(function (h) { if (!own(seen, h) && out.indexOf(h) < 0) out.push(h); });
  return out;
};
/* Documents d’essai (§2.5) : o = { sid, root, version, instrument, fingerprint, from, to, op, hashes, sr } ;
   ≤ 500 configHash par document. rnd : aléa [0, 1) (T.rng(graine) pour des identifiants reproductibles). */
LS.essaiDocs = function (o, now, rnd) {
  now = isNum(now) ? now : Date.now(); rnd = rnd || Math.random;
  var hs = o.hashes || [], sr = o.sr || [], out = [];
  for (var i = 0; i < hs.length; i += 500) {
    var a = ''; for (var k = 0; k < 6; k++) a += Math.floor(rnd() * 36).toString(36);
    out.push({ id: 'e' + now.toString(36) + a, sid: o.sid, root: o.root || o.sid, version: o.version, instrument: o.instrument, fingerprint: o.fingerprint, from: o.from, to: o.to, op: o.op, hashes: hs.slice(i, i + 500), sr: sr.slice(i, i + 500).map(function (x) { return isNum(x) ? x : null; }), at: now, u: now });
  }
  return out;
};
/* PBO par CSCV (T.lib.quant.cscv) sur la matrice des P&L nets par séance : mat[config][séance] = {net} ou nombre. */
LS.pbo = function (mat, nb) {
  if (!Array.isArray(mat) || mat.length < 2) return { value: null, error: 'il faut au moins deux configurations' };
  var perf = mat.map(function (row) { return (row || []).map(function (c) { return isNum(c) ? c : c && isNum(c.net) ? c.net : 0; }); });
  var r = QT().cscv(perf, nb || 8);
  r.value = r && isNum(r.pbo) ? r.pbo : null;
  return r;
};
function grid2(cells) { return Array.isArray(cells) && cells.length && !Array.isArray(cells[0]) ? [cells] : (cells || []); }
function cellVal(c) { return c == null ? NaN : isNum(c) ? c : isNum(c.meanR) ? c.meanR : NaN; }
function bestOf(G, best) {
  if (Array.isArray(best) && best.length === 2) return { x: best[0], y: best[1] };
  if (isObj(best)) { if (isNum(best.ix)) return { x: best.ix, y: best.iy || 0 }; if (isNum(best.i)) return { x: best.i, y: best.j || 0 }; if (isNum(best.x) && isNum(best.y)) return { x: best.x, y: best.y }; }
  var bx = -1, by = -1, bv = -Infinity;
  for (var y = 0; y < G.length; y++) for (var x = 0; x < G[y].length; x++) { var v = cellVal(G[y][x]); if (v > bv) { bv = v; bx = x; by = y; } }
  return bx < 0 ? null : { x: bx, y: by };
}
/* plateau(cells, best?) : moyenne des voisins (8, ou 2 en une dimension) divisée par le meilleur, sur meanR ;
   false si le meilleur ≤ 0 ou s’il n’a aucun voisin. Un voisin sans trade compte zéro (prudence).
   cells[ny][nx] (ou une liste en une dimension) ; best = [ix, iy] (convention de T.lib.perf), {ix, iy} ou absent
   (meilleure cellule, la première en cas d’égalité). */
LS.plateau = function (cells, best) {
  var G = grid2(cells), b = bestOf(G, best);
  if (!b || !G[b.y] || G[b.y][b.x] === undefined) return false;
  var bv = cellVal(G[b.y][b.x]);
  if (!(bv > 0)) return false;
  var ny = G.length, nx = G[0].length, oneD = ny === 1 || nx === 1, vals = [];
  for (var dy = -1; dy <= 1; dy++) for (var dx = -1; dx <= 1; dx++) {
    if (!dx && !dy) continue;
    if (oneD && dx && dy) continue;
    var y = b.y + dy, x = b.x + dx;
    if (y < 0 || y >= ny || x < 0 || !G[y] || x >= G[y].length) continue;
    var v = cellVal(G[y][x]); vals.push(isNum(v) ? v : 0);
  }
  return vals.length ? mean(vals) / bv : false;
};
/* stability(cells, o?) : part de la grille au-dessus d’un plancher (o.floor, 0 par défaut) parmi les cellules
   qui ont des trades, avec la médiane et les extrêmes. Sans avantage, chaque cellule tend vers −costR. */
LS.stability = function (cells, o) {
  o = o || {}; var floor = isNum(o.floor) ? o.floor : 0, G = grid2(cells), v = [];
  G.forEach(function (row) { (row || []).forEach(function (c) { if (c && isNum(c.n) && c.n === 0) return; var x = cellVal(c); if (isNum(x)) v.push(x); }); });
  if (!v.length) return { value: null, cells: 0, above: 0, floor: floor, median: NaN, min: NaN, max: NaN };
  var s = v.slice().sort(function (a, b) { return a - b; }), above = v.filter(function (x) { return x > floor; }).length, m = s.length;
  return { value: above / m, cells: m, above: above, floor: floor, median: m % 2 ? s[(m - 1) / 2] : (s[m / 2 - 1] + s[m / 2]) / 2, min: s[0], max: s[m - 1] };
};
/* SPRT de Wald. Normal : H0 mu0 = −costR (aucun avantage), H1 mu1 = borne basse à 90 % du bootstrap en
   échantillon ; incrément (mu1 − mu0)/σ² · (x − (mu0 + mu1)/2). Binomial exact (géométrie fixe) : p0 = equilibrium,
   p1 = taux en échantillon ; un gain (r > 0) ajoute ln(p1/p0), une perte (r < 0) ln((1 − p1)/(1 − p0)), r = 0 ne
   compte pas. Bornes ln((1 − β)/α) et ln(β/(1 − α)) ; arrêt au premier franchissement. mu1 ≤ mu0 → 'na'. */
LS.sprt = function (xs, o) {
  o = o || {}; xs = xs || [];
  var alpha = isNum(o.alpha) ? o.alpha : 0.05, beta = isNum(o.beta) ? o.beta : 0.20;
  var up = Math.log((1 - beta) / alpha), lo = Math.log(beta / (1 - alpha));
  var bin = o.form === 'binomial' || (o.form !== 'normal' && isNum(o.p0) && isNum(o.p1));
  var res = { form: bin ? 'binomial' : 'normal', decision: 'continuer', llr: 0, upper: up, lower: lo, n: 0, at: -1, path: [], alpha: alpha, beta: beta, wins: 0, losses: 0 };
  function na(why) { res.decision = 'na'; res.why = why; return res; }
  var inc;
  if (bin) {
    var p0 = o.p0, p1 = o.p1; res.p0 = p0; res.p1 = p1;
    if (!(p0 > 0 && p0 < 1 && p1 > 0 && p1 < 1)) return na('Taux hors de ]0, 1[ : le test binomial n’a pas de sens.');
    if (!(p1 > p0)) return na('Le taux en échantillon ne dépasse pas le taux d’équilibre : il n’y a pas d’avantage à confirmer.');
    var lw = Math.log(p1 / p0), ll = Math.log((1 - p1) / (1 - p0));
    res.incWin = lw; res.incLoss = ll;
    inc = function (x) { return x > 0 ? lw : x < 0 ? ll : null; };
  } else {
    var m0 = o.mu0, m1 = o.mu1, sg = o.sigma; res.mu0 = m0; res.mu1 = m1; res.sigma = sg;
    if (!isNum(m0) || !isNum(m1)) return na('H0 ou H1 manquant.');
    if (!(m1 > m0)) return na('La borne basse du bootstrap ne dépasse pas −costR : rien ne sépare l’échantillon de l’absence d’avantage.');
    if (!(sg > 0)) return na('Écart-type inconnu.');
    var k = (m1 - m0) / (sg * sg), mid = (m0 + m1) / 2;
    inc = function (x) { return isNum(x) ? k * (x - mid) : null; };
  }
  for (var i = 0; i < xs.length; i++) {
    var d = inc(xs[i]); if (d === null) continue;
    res.n++; if (bin) { if (xs[i] > 0) res.wins++; else res.losses++; }
    res.llr += d; res.path.push(res.llr);
    if (res.llr >= up) { res.decision = 'avantage-confirme'; res.at = i; break; }
    if (res.llr <= lo) { res.decision = 'aucun-avantage'; res.at = i; break; }
  }
  return res;
};
/* Géométrie fixe (§5) : objectif en R, sans break-even, suiveur ni maxBars → test binomial exact. */
LS.fixedGeometry = function (spec) {
  var s = spec && spec.long ? spec : null; if (!s) return false;
  var m = s.manage || {}, rules = [s.long].concat(s.mirror === false && s.short ? [s.short] : []);
  return rules.every(function (r) { return r && r.target && r.target.type === 'r'; }) && !m.breakeven && !m.trail && m.maxBars == null;
};
/* Options du SPRT d’une version : is = statistiques en échantillon (4.1), bootLo = borne basse à 90 % de meanR. */
LS.sprtPlan = function (spec, is, bootLo) {
  is = is || {};
  if (LS.fixedGeometry(spec)) return { form: 'binomial', p0: is.equilibrium, p1: is.winRate };
  return { form: 'normal', mu0: -is.costR, mu1: bootLo, sigma: is.sdR };
};
/* Trades de suivi d’une version scellée (§5) : du journal, portant strat = sid et stratV = version, pris, clos,
   avec un R, postérieurs à sealedAt, dans l’ordre de décision. */
LS.followTrades = function (rows, version) {
  if (!version || !isNum(version.sealedAt)) return [];
  return (rows || []).filter(function (r) { return r && !r.deleted && r.strat === version.sid && r.stratV === version.version && r.kind === 'pris' && r.status === 'clos' && isNum(r.r) && isNum(r.at) && r.at > version.sealedAt; })
    .sort(function (a, b) { return a.at - b.at || (a.closedAt || 0) - (b.closedAt || 0); });
};
/* CUSUM tabulaire : neg cumule les chutes sous target (alarme d’usure), pos les hausses. k (référence) et h
   (seuil) dans l’unité des xs ; défauts 0,5 et 4. Loi nulle : arl0 = nombre moyen d’observations avant une
   fausse alarme sans changement (approximation de Siegmund, observations normales d’écart-type sigma). */
LS.cusum = function (xs, target, k, h, sigma) {
  xs = xs || []; target = isNum(target) ? target : 0; k = isNum(k) ? k : 0.5; h = isNum(h) ? h : 4;
  var sp = 0, sn = 0, pos = [], neg = [], alarm = -1, alarmUp = -1;
  for (var i = 0; i < xs.length; i++) {
    var x = xs[i]; if (!isNum(x)) { pos.push(sp); neg.push(sn); continue; }
    sp = Math.max(0, sp + x - target - k); sn = Math.max(0, sn + target - k - x);
    pos.push(sp); neg.push(sn);
    if (alarm < 0 && sn > h) alarm = i;
    if (alarmUp < 0 && sp > h) alarmUp = i;
  }
  var sg = isNum(sigma) && sigma > 0 ? sigma : xs.length >= 2 ? sdev(xs.filter(isNum)) : NaN;
  return { pos: pos, neg: neg, alarm: alarm, alarmUp: alarmUp, last: { pos: sp, neg: sn }, target: target, k: k, h: h, sigma: sg, arl0: LS.cusumArl0(k, h, sg) };
};
LS.cusumArl0 = function (k, h, sigma) {
  if (!(sigma > 0)) return NaN;
  var kk = k / sigma, b = h / sigma + 1.166;
  if (Math.abs(kk) < 1e-9) return b * b;
  return (Math.exp(2 * kk * b) - 2 * kk * b - 1) / (2 * kk * kk);
};

/* ================================================================================================
   9. Gabarits (§5) : des points de départ. Aucun ne prétend à un avantage ; tous passent normalize.
   ================================================================================================ */
var NEUTRE = ' Point de départ : aucun avantage n’est supposé ; le test, ses lois nulles et le registre des essais le diront.';
LS.TEMPLATES = [
  { id: 'vwap-rejet', label: 'Rejet de bande VWAP',
    description: 'Achat quand le prix, sous la VWAP de séance, redescend toucher la bande inférieure puis clôture au-dessus ; vente en miroir sur la bande supérieure. Stop au-delà de la bande, objectif sur la VWAP relue à chaque barre.' + NEUTRE,
    spec: { name: 'Rejet de bande VWAP', hypothesis: '', side: 'both', mirror: true,
      long: { setup: [{ cmp: '<', a: { f: 'close' }, b: { f: 'vwap' } }], trigger: { reject: { f: 'vwap', k: '$bande' }, from: 'above' }, entry: { type: 'market' }, stop: { type: 'level', at: { f: 'vwap', k: '$bande' }, buffer: '$marge' }, target: { type: 'level', at: { f: 'vwap' }, dynamic: true } },
      risk: { cooldown: 1 },
      params: { bande: { v: -2, min: -3, max: -1, step: 0.5, label: 'Bande VWAP en σ (négative à l’achat)' }, marge: { v: 8, min: 0, max: 20, step: 4, label: 'Marge du stop (ticks)' } } } },
  { id: 'or-cassure', label: 'Cassure du range d’ouverture',
    description: 'Range des quinze premières minutes de la séance régulière ; achat quand une clôture casse son haut, vente en miroir sous son bas. Stop au milieu du range, objectif en multiple du risque, une entrée par séance.' + NEUTRE,
    spec: { name: 'Cassure du range d’ouverture', hypothesis: '', anchor: 'rth', side: 'both', mirror: true,
      session: { tz: NY, from: '09:45', to: '11:30', flat: '15:50', days: [1, 2, 3, 4, 5], warmup: 15 },
      long: { setup: [], trigger: { 'break': { f: 'or', from: '09:30', to: '09:45', of: 'high' }, dir: 'up' }, entry: { type: 'market' }, stop: { type: 'level', at: { f: 'or', from: '09:30', to: '09:45', of: 'mid' }, buffer: 2 }, target: { type: 'r', value: '$rr' } },
      risk: { maxPerSession: 1 },
      params: { rr: { v: 2, min: 1, max: 3, step: 0.5, label: 'Objectif (R)' } } } },
  { id: 'rsi-retour', label: 'Retour à la moyenne RSI',
    description: 'Achat quand le RSI repasse au-dessus d’un seuil bas ; vente en miroir quand il repasse sous le seuil symétrique (100 moins le seuil). Stop en ATR, objectif en multiple du risque, sortie au bout de trente barres.' + NEUTRE,
    spec: { name: 'Retour à la moyenne RSI', hypothesis: '', side: 'both', mirror: true,
      long: { setup: [], trigger: { cross: 'up', a: { f: 'rsi', n: '$n' }, b: '$seuil' }, entry: { type: 'market' }, stop: { type: 'atr', value: 1.5, n: 14 }, target: { type: 'r', value: 1.5 } },
      manage: { maxBars: 30 },
      params: { n: { v: 14, min: 7, max: 21, step: 7, label: 'Longueur du RSI (barres)' }, seuil: { v: 30, min: 20, max: 35, step: 5, label: 'Seuil bas du RSI' } } } },
  { id: 'veille-rejet', label: 'Rejet du haut ou du bas de la veille',
    description: 'Achat quand le prix redescend toucher le plus bas de la séance précédente puis clôture au-dessus ; vente en miroir sur le plus haut de la veille. Stop au-delà du dernier creux, objectif en multiple du risque.' + NEUTRE,
    spec: { name: 'Rejet du bas de la veille', hypothesis: '', side: 'both', mirror: true,
      long: { setup: [], trigger: { reject: { f: 'prev', of: 'low' }, from: 'above' }, entry: { type: 'market' }, stop: { type: 'swing', n: 5, buffer: 2 }, target: { type: 'r', value: '$rr' } },
      params: { rr: { v: 2, min: 1, max: 3, step: 0.5, label: 'Objectif (R)' } } } },
  { id: 'ema-poursuite', label: 'Poursuite au-dessus de l’EMA',
    description: 'Achat quand, au-dessus d’une moyenne exponentielle lente, la clôture repasse au-dessus d’une moyenne rapide ; vente en miroir sous les deux. Stop au-delà du dernier creux, objectif en multiple du risque.' + NEUTRE,
    spec: { name: 'Poursuite au-dessus de l’EMA', hypothesis: '', side: 'both', mirror: true,
      long: { setup: [{ cmp: '>', a: { f: 'close' }, b: { f: 'ema', n: '$lente' } }], trigger: { cross: 'up', a: { f: 'close' }, b: { f: 'ema', n: '$rapide' } }, entry: { type: 'market' }, stop: { type: 'swing', n: 10, buffer: 1 }, target: { type: 'r', value: 2 } },
      params: { rapide: { v: 20, min: 10, max: 30, step: 5, label: 'EMA rapide (barres)' }, lente: { v: 50, min: 40, max: 100, step: 10, label: 'EMA lente (barres)' } } } },
  { id: 'gex-proche', label: 'Rejet du niveau GEX le plus proche',
    description: 'Achat quand le prix redescend toucher le niveau nommé le plus proche sous lui puis clôture au-dessus ; vente en miroir sur le plus proche au-dessus. Stop au-delà du niveau, objectif sur le niveau suivant. Exige des niveaux par séance et un jeu dont le raccord des contrats est connu.' + NEUTRE,
    spec: { name: 'Rejet du niveau le plus proche', hypothesis: '', side: 'both', mirror: true,
      long: { setup: [], trigger: { reject: { f: 'nearest', side: 'below' }, from: 'above' }, entry: { type: 'market' }, stop: { type: 'level', at: { f: 'nearest', side: 'below' }, buffer: '$marge' }, target: { type: 'level', at: { f: 'nearest', side: 'above' }, dynamic: false } },
      params: { marge: { v: 8, min: 4, max: 16, step: 4, label: 'Marge du stop (ticks)' } } } }
];
/* Un gabarit en brouillon neuf : identité posée par l’appelant (sid), spec normalisée. */
LS.fromTemplate = function (id, sid, now) {
  var t = LS.TEMPLATES.filter(function (x) { return x.id === id; })[0];
  if (!t) throw new Error('Gabarit inconnu : « ' + id + ' ».');
  var s = clone(t.spec); now = isNum(now) ? now : Date.now();
  if (sid) { s.sid = sid; s.root = sid; s.version = 1; s.id = sid + '_v1'; }
  s.status = 'brouillon'; s.hash = null; s.sealedAt = null; s.createdAt = now; s.u = now; s.template = id;
  return LS.normalize(s).spec;
};

/* ================================================================================================
   10. Verdict (§5). Les seuils sont des constantes du code, chacune avec sa justification ; aucun n’est tiré
       de ce qu’il sert à évaluer (règle 6 du dépôt ALP).
   ================================================================================================ */
LS.GATES = {
  /* 1. Échantillon : route 1 d’ALP nº 3 (huitième partie, table 14) — un Sharpe de référence DÉCLARÉ de 0,10
     par trade, test unilatéral à 5 %, puissance 80 % : 619 trades. Jamais calculé depuis le Sharpe observé,
     sinon un très mauvais résultat exigerait un petit échantillon et passerait. */
  sample: { sr: 0.10, alpha: 0.05, power: 0.80, source: 'ALP nº 3, huitième partie, table 14' },
  /* 2. Entrées au hasard (même exécution, même nombre de signaux par séance) : le moment d’entrée doit faire
     mieux que le hasard au seuil usuel de 5 %, avant toute correction de multiplicité (le DSR la porte). */
  randomP: 0.05,
  /* 3. Permutation intra-tranche : même seuil, contre une hypothèse nulle qui garde la volatilité de la journée. */
  permuteP: 0.05,
  /* 4. Sharpe déflaté : probabilité ≥ 95 % que le Sharpe dépasse le maximum attendu de N essais sans avantage
     (N et leur dispersion lus au registre, jamais estimés à la main). */
  dsr: 0.95,
  /* 5. Probabilité de surajustement (CSCV) : au plus une chance sur cinq que la meilleure configuration en
     échantillon tombe sous la médiane hors échantillon ; 0,5 est le hasard pur. */
  pbo: 0.2,
  /* 6. Plateau : les voisins doivent garder 70 % du meilleur résultat ; un pic isolé est un artefact de grille. */
  plateau: 0.7,
  /* 7. Coûts : l’espérance doit rester positive aux planchers, puis encore à un tick de plus par jambe glissée
     (ou à un tick de dépassement exigé des limites si aucune jambe ne glisse). */
  stressTicks: 1,
  /* 8. Efficacité de l’analyse en avant : la moitié au moins de l’espérance des meilleurs en échantillon doit
     survivre hors échantillon ; en dessous, l’optimisation explique l’essentiel du résultat. */
  wfe: 0.5,
  /* 9. Hors échantillon : entrées au hasard rejouées sur les seules séances hors échantillon, même seuil que 2,
     à la première ouverture de la lignée seulement (une seconde ouverture est un essai de plus). */
  oosP: 0.05,
  /* Rejet franc : une espérance qui ne dépasse pas le coût seul (−costR), ou un tirage au hasard qui fait aussi
     bien une fois sur deux, ne laisse rien à approfondir. */
  rejectP: 0.5,
  /* Planchers de coûts du verdict : commission au moins égale au réglage de l’utilisateur (une commission
     déclarée plus basse ne s’applique pas), glissement d’au moins un tick par jambe exécutée au marché ou au
     stop — la plus petite perte possible sur un carnet au tick. */
  floors: { slipTicks: 1, commission: 'reglage' }
};
LS.floorCosts = function (costs, userCommission) {
  costs = costs || {}; var u = isNum(userCommission) ? userCommission : 0;
  var c = isNum(costs.commissionRT) ? Math.max(costs.commissionRT, u) : u, sl = Math.max(isNum(costs.slipTicks) ? costs.slipTicks : 0, LS.GATES.floors.slipTicks);
  return { commissionRT: c, slipTicks: sl, raised: c !== costs.commissionRT || sl !== costs.slipTicks };
};
LS.sampleMin = function () { var G = LS.GATES.sample; return QT().route1(G.sr, G.alpha, G.power); };
/* Avant l’ouverture hors échantillon : trades attendus (taux en échantillon × séances hors échantillon) et nombre
   requis pour séparer meanR de −costR (unilatéral 5 %, puissance 80 %). */
LS.oosPlan = function (o) {
  o = o || {};
  var rate = o.sessionsIS > 0 ? o.nIS / o.sessionsIS : NaN, exp = rate * o.sessionsOOS, edge = o.meanR + o.costR;
  var req = edge > 0 && o.sdR > 0 ? QT().route1(edge / o.sdR, 0.05, 0.80) : Infinity;
  return { rate: rate, expected: exp, required: req, enough: isNum(exp) && exp >= req };
};
function pOf(x) { return isNum(x) ? x : x && isNum(x.p) ? x.p : null; }
function vOf(x, k) { return isNum(x) ? x : x && isNum(x[k]) ? x[k] : null; }
/* verdict(r) → { items: [{ id, label, value, x, need, pass, why }], level, text }. Entrées (aux coûts planchers) :
   r = { n, meanR, costR, random: {p}|p|null, permute: {p}|p|null, dsr: {dsr}|nombre|null, N,
         pbo: nombre|{pbo}|'na'|null, plateau: nombre|false|'na'|null,
         costs: { floor (meanR aux planchers), plus1 (à +1 tick par jambe), through1 (à 1 tick de dépassement),
                  na (aucune jambe glissée) } | null,
         wfa: { wfe: nombre|null } | 'na' | null,
         oos: { sealed, altered, first, p, prior: { version, at } } | null,
         blocked: texte (ex. migration incomplète) | null }.
   pass : true, false, null (applicable, pas encore calculé : empêche « prête »), 'na' (sans objet). */
LS.verdict = function (r) {
  r = r || {};
  var G = LS.GATES, F = T.fmt, items = [];
  function it(id, label, value, x, need, pass, why) { items.push({ id: id, label: label, value: value, x: isNum(x) ? x : null, need: need, pass: pass, why: why }); }
  function p3(x) { return F.num(x, 3); }
  /* 1 */
  var nMin = LS.sampleMin(), n = isNum(r.n) ? r.n : null;
  it('echantillon', 'Échantillon', n === null ? '—' : F.int(n) + ' trades', n, '≥ ' + F.int(nMin), n === null ? null : n >= nMin,
    n === null ? 'Pas encore de run en échantillon.' : n >= nMin ? 'Assez de trades pour séparer un Sharpe de 0,10 par trade du hasard (' + G.sample.source + ').' : 'Il en faut ' + F.int(nMin) + ' pour séparer un Sharpe de 0,10 par trade du hasard (5 %, puissance 80 %) ; il en manque ' + F.int(nMin - n) + '.');
  /* 2, 3 */
  var pr = pOf(r.random), pp = pOf(r.permute);
  it('hasard', 'Entrées au hasard', pr === null ? '—' : 'p = ' + p3(pr), pr, 'p < ' + F.num(G.randomP, 2), pr === null ? null : pr < G.randomP,
    pr === null ? 'Pas encore calculées.' : pr < G.randomP ? 'Les mêmes ordres posés au hasard font moins bien dans plus de 95 % des tirages.' : 'Le moment d’entrée ne se sépare pas du hasard : des entrées tirées au sort font aussi bien.');
  it('permutation', 'Prix permutés', pp === null ? '—' : 'p = ' + p3(pp), pp, 'p < ' + F.num(G.permuteP, 2), pp === null ? null : pp < G.permuteP,
    pp === null ? 'Pas encore calculés.' : pp < G.permuteP ? 'L’ordre des minutes porte quelque chose que la permutation détruit.' : 'Les prix permutés dans chaque tranche de 30 minutes donnent un résultat comparable.');
  /* 4 */
  var d = vOf(r.dsr, 'dsr');
  it('dsr', 'Sharpe déflaté', d === null ? '—' : F.pct(d, 1), d, '≥ ' + F.pct(G.dsr, 0), d === null ? null : d >= G.dsr,
    d === null ? 'Pas encore calculé.' : (isNum(r.N) ? 'Avec N = ' + F.int(r.N) + ' essais comptés au registre : ' : '') + (d >= G.dsr ? 'le Sharpe dépasse ce que le meilleur de ces essais donnerait sans avantage.' : 'le Sharpe ne dépasse pas assez ce que le meilleur de ces essais donnerait sans avantage.'));
  /* 5, 6 */
  var noSweep = 'Pas de balayage : rien n’a été choisi parmi plusieurs configurations.';
  if (r.pbo === 'na') it('pbo', 'Surajustement (PBO)', 'sans objet', null, '≤ ' + F.pct(G.pbo, 0), 'na', noSweep);
  else { var pb = vOf(r.pbo, 'pbo'); it('pbo', 'Surajustement (PBO)', pb === null ? '—' : F.pct(pb, 0), pb, '≤ ' + F.pct(G.pbo, 0), pb === null ? null : pb <= G.pbo, pb === null ? 'Pas encore calculé.' : pb <= G.pbo ? 'La meilleure configuration reste dans la moitié haute hors échantillon dans au moins 80 % des découpages.' : 'La meilleure configuration retombe trop souvent sous la médiane hors échantillon.'); }
  if (r.plateau === 'na') it('plateau', 'Plateau', 'sans objet', null, '≥ ' + F.num(G.plateau, 1), 'na', noSweep);
  else if (r.plateau === false) it('plateau', 'Plateau', 'aucun', null, '≥ ' + F.num(G.plateau, 1), false, 'La meilleure cellule ne dépasse pas zéro : il n’y a pas de sommet à mesurer.');
  else { var pl = isNum(r.plateau) ? r.plateau : null; it('plateau', 'Plateau', pl === null ? '—' : F.num(pl, 2), pl, '≥ ' + F.num(G.plateau, 1), pl === null ? null : pl >= G.plateau, pl === null ? 'Pas encore calculé.' : pl >= G.plateau ? 'Les réglages voisins gardent l’essentiel du meilleur résultat.' : 'Le meilleur réglage est un pic : ses voisins perdent l’essentiel du résultat.'); }
  /* 7 */
  var c = r.costs;
  if (!c || !isNum(c.floor) || (c.na ? !isNum(c.through1) : !isNum(c.plus1))) it('couts', 'Coûts', '—', null, 'meanR > 0', null, 'Stress des coûts pas encore calculé.');
  else {
    var second = c.na ? c.through1 : c.plus1, okc = c.floor > 0 && second > 0;
    it('couts', 'Coûts', F.r(c.floor, 3) + ' puis ' + F.r(second, 3), c.floor, 'meanR > 0', okc,
      'Espérance de ' + F.r(c.floor, 3) + ' aux coûts planchers, puis ' + F.r(second, 3) + (c.na ? ' quand les limites exigent un tick de dépassement (aucune jambe ne glisse).' : ' à un tick de plus par jambe glissée.') + (okc ? '' : ' Le résultat ne survit pas à un coût réaliste.'));
  }
  /* 8 */
  if (r.wfa === 'na') it('wfe', 'Analyse en avant (WFE)', 'sans objet', null, '≥ ' + F.num(G.wfe, 1), 'na', 'Pas d’analyse en avant : aucun réglage n’a été choisi fenêtre par fenêtre.');
  else if (!r.wfa) it('wfe', 'Analyse en avant (WFE)', '—', null, '≥ ' + F.num(G.wfe, 1), null, 'Pas encore calculée.');
  else if (!isNum(r.wfa.wfe)) it('wfe', 'Analyse en avant (WFE)', 'indéfinie', null, '≥ ' + F.num(G.wfe, 1), false, 'Les meilleurs réglages en échantillon ne dépassent pas le coût : l’efficacité n’a pas de dénominateur.');
  else it('wfe', 'Analyse en avant (WFE)', F.num(r.wfa.wfe, 2), r.wfa.wfe, '≥ ' + F.num(G.wfe, 1), r.wfa.wfe >= G.wfe, r.wfa.wfe >= G.wfe ? 'Au moins la moitié de l’espérance choisie en échantillon survit hors échantillon.' : 'L’essentiel de l’espérance choisie en échantillon disparaît hors échantillon.');
  /* 9 */
  var o = r.oos;
  if (!o) it('oos', 'Hors échantillon', '—', null, 'p < ' + F.num(G.oosP, 2), null, 'Pas encore ouvert : scellez la version, puis ouvrez le hors échantillon une seule fois.');
  else if (o.altered) it('oos', 'Hors échantillon', 'version altérée', null, 'p < ' + F.num(G.oosP, 2), false, 'Le hachage ne correspond plus à la version scellée : le hors échantillon ne compte pas.');
  else if (!o.sealed) it('oos', 'Hors échantillon', '—', null, 'p < ' + F.num(G.oosP, 2), null, 'Version non scellée : le hors échantillon ne s’ouvre qu’après scellement.');
  else if (o.first === false) it('oos', 'Hors échantillon', 'déjà vu', null, 'p < ' + F.num(G.oosP, 2), false, 'Hors échantillon déjà vu par la lignée' + (o.prior && o.prior.version != null ? ' (version ' + o.prior.version + (isNum(o.prior.at) ? ', le ' + F.dateLong(o.prior.at) : '') + ')' : '') + ' : il ne peut plus servir de preuve.');
  else { var po = pOf(o); it('oos', 'Hors échantillon', po === null ? '—' : 'p = ' + p3(po), po, 'p < ' + F.num(G.oosP, 2), po === null ? null : po < G.oosP, po === null ? 'Ouvert, entrées au hasard pas encore rejouées sur ses séances.' : po < G.oosP ? 'Sur les seules séances hors échantillon, le hasard fait moins bien dans plus de 95 % des tirages.' : 'Hors échantillon, le moment d’entrée ne se sépare pas du hasard.'); }

  /* niveau */
  var fails = items.filter(function (x) { return x.pass === false; }), nulls = items.filter(function (x) { return x.pass === null; });
  var under = isNum(r.meanR) && isNum(r.costR) && r.meanR <= -r.costR, coin = pr !== null && pr >= G.rejectP, level, text;
  if (under || coin) {
    level = 'rejetee';
    text = 'Rejetée : ' + (under ? 'l’espérance (' + F.r(r.meanR, 3) + ') ne dépasse pas ce que coûte une stratégie sans avantage (' + F.r(-r.costR, 3) + ')' : '') + (under && coin ? ', et ' : '') + (coin ? 'des entrées tirées au hasard font aussi bien une fois sur deux (p = ' + p3(pr) + ')' : '') + '.';
  } else if (fails.length) {
    level = 'a-approfondir';
    text = 'À approfondir : ' + fails.length + ' critère' + (fails.length > 1 ? 's ne tiennent' : ' ne tient') + ' pas (' + fails.map(function (x) { return lowFirst(x.label); }).join(', ') + ').' + (nulls.length ? ' ' + nulls.length + ' autre' + (nulls.length > 1 ? 's restent' : ' reste') + ' à calculer.' : '');
  } else if (nulls.length) {
    level = 'a-approfondir';
    text = 'À approfondir : ' + nulls.length + ' critère' + (nulls.length > 1 ? 's restent' : ' reste') + ' à calculer (' + nulls.map(function (x) { return lowFirst(x.label); }).join(', ') + ').';
  } else if (r.blocked) {
    level = 'a-approfondir'; text = 'À approfondir : ' + r.blocked;
  } else {
    level = 'prete-simulateur';
    text = 'Prête pour le simulateur : les critères tiennent aux coûts planchers. Ce n’est pas une promesse de gain ; le simulateur puis le suivi le diront.';
  }
  return { items: items, level: level, text: T.typo ? T.typo(text) : text };
};
LS.LEVELS = { 'rejetee': 'Rejetée', 'a-approfondir': 'À approfondir', 'prete-simulateur': 'Prête pour le simulateur' };
LS.FINS = { stop: 'Stop', be: 'Break-even', trail: 'Suiveur', objectif: 'Objectif', temps: 'Temps écoulé', flat: 'Sortie forcée', cloche: 'Fin de séance', oppose: 'Signal opposé' };
LS.COUNTS = { signals: 'Signaux', ambigu: 'Ambigus (achat et vente)', taille: 'Taille nulle', stopcourt: 'Stop trop court', ecart: 'Exécution au-delà du stop', annule: 'Annulés (niveau indéfini)', expire: 'Expirés', trou: 'Trou de données', marketable: 'Limites parties au marché', limite: 'Refusés par une limite de séance' };
