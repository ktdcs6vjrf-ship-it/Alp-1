/* Desk « Stratégie intraday » : le plan VWAP en trois étapes, la grammaire du setup, le seuil µ*, le catalogue des quinze lectures.
   Sources, contrôlées par test/micro.test.js :
   – plan : le plan VWAP de nuit de l’utilisateur (plan-vwap), dont chaque chiffre vient d’ALP nº 3 (parties III, XII, XVII, XIX) ;
   – setups : ALP nº 3, partie III, tables 6, 7 et 8 ; seuils déclarés dans alp1/setups.py
     (MULT_VOLUME 1,5 · Z_ABSORPTION 0,25 · PART_MECHE 0,60 · DEPASSEMENT 1 σ · PART_DELTA 1/3 · FENETRE 15 min) ;
   – seuil : port exact de calcFactory (plan-seance), vérifiée contre alp1 (horizon, seuil, speculation, entropy) :
     stop 0,6 pt (0,010 %) à 1:20 → µ* 8,189 pt/h et 474 décisions ; 3 pt (0,050 %) → 10 568 décisions ; 9 pt (0,150 %) → 0,196 pt/h ;
   – lectures : ALP nº 3, partie III, tables 2, 3 et 5. Aucune valeur n’est inventée : une valeur absente se lit « — ». */
var h = T.h, U = T.ui, C = T.chart, F = T.fmt;
T.lib = T.lib || {};
var L = T.lib.micro = {};
var K = { plan: 'micro:plan', seuil: 'micro:seuil', lect: 'micro:lecture', nqBias: 'nq:bias', draft: 'journal:draft' };
L.KEYS = K;

/* =====================================================================
   1. Fonctions pures — aucun DOM, aucun T.store
   ===================================================================== */
function fin(v) { return typeof v === 'number' && isFinite(v); }
L.fin = fin;
function pad2(n) { return String(n).padStart(2, '0'); }
L.dayKeyOf = function (ms) { var p = T.time.parts('Europe/Paris', new Date(ms)); return p.y + '-' + pad2(p.mo) + '-' + pad2(p.d); };

/* ---------- 1.1 Le plan VWAP de nuit (porté de plan-vwap) ---------- */
L.STAGE_KEYS = ['T', 'B', 'P'];
L.STAGE_OF = { T: 'biais', B: 'vwap', P: 'declencheur', X: 'declencheur' };
L.STAGE_NAME = { T: 'tendance', B: 'VWAP', P: 'déclencheur' };
L.SIGNALS = [{ v: 'rejet', label: 'Rejet' }, { v: 'absorption', label: 'Absorption' }];
L.DIRS = ['long', 'both', 'short'];
function hh(n) { return pad2(n) + ' h'; }
function hourWord(n) { return n === 0 ? 'minuit' : n + ' h'; }
L.window = function (set) { var a = set && fin(set.winFrom) ? set.winFrom : 0, b = set && fin(set.winTo) ? set.winTo : 9; return { from: a, to: b, range: hh(a) + ' – ' + hh(b) }; };

L.stages = function (set) {
  var w = L.window(set);
  return [
    { k: 'T', title: 'Tendance + GEX', sub: 'Le biais et le régime · une fois par séance', k5: 'On regarde de quel côté coule la rivière avant de mettre le bateau à l’eau.', items: [
      { t: 'Structure', s: 'Sur ton unité de tendance (ex. H1), sommets et creux montants : biais acheteur ; descendants : biais vendeur ; sinon neutre. Les pivots disent surtout où poser le stop : le biais est un choix que tu déclares, pas un signal.', k: 'Si chaque marche de l’escalier est plus haute que la précédente, on dit que ça monte. Mais l’escalier ne promet pas la marche suivante.' },
      { t: 'Niveaux GEX reportés', s: 'Place HVL, CR, PS et GW du jour. Ce sont des zones larges, environ 1,2 écart-type de la journée, pas des prix exacts. Le HVL n’est jamais un prix d’entrée ni de stop.', k: 'Les niveaux GEX sont de gros coussins posés sur la route : le prix peut rebondir dessus, mais ce sont des coussins, pas des traits fins.' },
      { t: 'Régime gamma lu', s: 'Prix au-dessus du HVL : gamma positif, le marché tourne plutôt en rond. En dessous : gamma négatif, mouvements plus amples, taille réduite. Le gamma règle la taille et la durée, jamais le sens.', k: 'Au-dessus de la ligne, le marché se balance doucement. En dessous, il saute comme sur un trampoline : on fait de plus petits sauts.' }] },
    { k: 'B', title: 'Filtre VWAP', sub: 'Le bon côté de la moyenne · ' + w.range, k5: 'On ne pêche qu’au bon endroit et au bon moment.', win: true, items: [
      { t: 'Dans la fenêtre ' + w.range, s: 'Cherche des trades seulement entre ' + hourWord(w.from) + ' et ' + hourWord(w.to) + '. La VWAP part de l’ouverture Globex, minuit à Paris. Ta fenêtre se prouve avec ton journal, pas avec le document.', k: 'On ne joue que pendant la récréation du matin, quand la cour est calme.' },
      { t: 'Bon côté de la VWAP', dyn: 'vwap', s: '', k: 'La VWAP, c’est le prix moyen de la journée, comme la ligne au milieu du terrain. On vend quand le prix est monté trop haut au-dessus, on achète quand il est descendu trop bas en dessous.' },
      { t: 'Contact de la bande ±2σ', s: 'Attends que le prix touche la bande à deux écarts-types : un niveau recalculé chaque minute, le plus touché du catalogue (12,68 contacts par séance dans le document). Jamais au milieu, jamais à l’œil.', k: 'On attend que l’élastique soit bien tiré avant de le lâcher.' },
      { t: 'Stop hors du bruit', s: 'Stop au-delà de la bande, plus large qu’une minute de bruit.', k: 'On pose le filet assez loin pour qu’un petit coup de vent ne le touche pas.' },
      { t: 'Tenue ≥ 8,4 min', s: 'Un trade plus court ne paie pas sa friction sur NQ (0,45 pt) : il faudrait une dérive au-delà de 3,2 pt/h.', k: 'Si on ne court que trois pas, le ticket d’entrée coûte plus cher que la course.' }] },
    { k: 'P', title: 'Déclencheur', sub: 'Le signal convenu, puis l’ordre', k5: 'On n’appuie sur le bouton que quand le signe convenu arrive.', items: [
      { t: 'Un seul signal, écrit d’avance', s: 'Rejet : mèche au-delà de la bande ≥ 60 % de la barre, clôture revenue dedans. Ou absorption : volume ≥ 1,5 × la médiane, |z| < 0,25, clôture qui ne franchit pas. Le rejet est le signal naturel d’un retour à la moyenne.', k: 'On attend que la balle rebondisse sur le mur avant de courir. Un seul signe, toujours le même.' },
      { t: 'Pas de second signal', s: 'Ajouter une condition pour se rassurer divise les occasions sans améliorer la chance : 48,7 % confirmé contre 49,4 % au contact brut.', k: 'Demander trois fois la permission ne rend pas la réponse plus sûre.' },
      { t: 'Ordre limite sur la bande', s: 'Poste l’ordre à la bande, pas au marché. Sur l’ES du document, le seuil est divisé par 2,22.', k: 'On attend le prix qu’on veut au lieu de payer plus cher pour aller vite.' },
      { t: 'Invalidation à 15 min', s: 'Si une clôture d’une minute traverse la bande de plus d’1 écart-type dans les 15 min, sors.', k: 'Si la balle passe à travers le mur au lieu de rebondir, on s’en va tout de suite.' }] }
  ];
};
L.TRADE = {
  k5: 'Le jeu s’arrête de quatre façons seulement. On écrit dans le cahier avant de savoir si on a gagné, et on ne change pas les règles en cours de partie.',
  rules: function (set) { var w = L.window(set); return [['Objectif :', 'retour à la VWAP.'], ['Quatre fins :', 'stop, VWAP atteinte, démenti à 15 min, ou ' + hourWord(w.to) + ' (fin de ta fenêtre).'], ['Rien d’autre :', 'ni point mort, ni stop suiveur. Ils raccourcissent l’exposition (−0,164 R et −1,353 R dans le document).'], ['Avant l’issue :', 'note l’heure, le niveau, le sens, la mise et ta conviction.']]; }
};
L.FOOT = { n: 'Sans dérive, chaque filtre réduit les occasions sans déplacer l’espérance (ALP nº 3, partie III). Ce plan sert à décider toujours de la même façon et à tout inscrire, refus compris. Le biais de l’étape 1, la lecture la moins prouvable, ne se décide qu’une fois par séance.', k: 'Un filtre ne rend pas le jeu plus facile à gagner. Il t’aide à jouer toujours pareil, et à tout écrire dans ton cahier, même quand tu choisis de ne pas jouer.' };
L.vwapSub = function (d) {
  if (d === 'long') return 'Biais acheteur : achète seulement sous la VWAP, à la bande −2σ. Aucun short aujourd’hui.';
  if (d === 'short') return 'Biais vendeur : vends seulement au-dessus de la VWAP, à la bande +2σ. Aucun long aujourd’hui.';
  return 'Short seulement au-dessus de la VWAP, à +2σ. Long seulement en dessous, à −2σ. Choisis le biais à l’étape 1 pour n’en garder qu’un.';
};
L.COUNTS = (function () { var o = {}; L.stages().forEach(function (s) { o[s.k] = s.items.length; }); return o; })();

L.normPlan = function (raw, today) {
  var s = raw && typeof raw === 'object' ? raw : {}, same = s.date === today, ch = same && s.checks && typeof s.checks === 'object' ? s.checks : {};
  function arr(x, n) { var o = []; for (var i = 0; i < n; i++) o.push(!!(Array.isArray(x) && x[i])); return o; }
  return {
    date: today,
    checks: { T: arr(ch.T, L.COUNTS.T), B: arr(ch.B, L.COUNTS.B), P: arr(ch.P, L.COUNTS.P) },
    dir: same && L.DIRS.indexOf(s.dir) >= 0 ? s.dir : null,
    dirAt: same && fin(s.dirAt) ? s.dirAt : 0,
    side: same && (s.side === 'long' || s.side === 'short') ? s.side : null,
    sig: s.sig === 'absorption' ? 'absorption' : 'rejet',
    kid: !!s.kid
  };
};
L.normDir = function (v) {
  var t = String(v == null ? '' : v).toLowerCase().trim();
  if (!t) return null;
  if (/^(long|acheteur|achat|achats|buy|bull|haussier|hausse|up)\b/.test(t)) return 'long';
  if (/^(short|vendeur|vente|ventes|sell|bear|baissier|baisse|down)\b/.test(t)) return 'short';
  if (/^(neutre|neutral|both|flat|aucun|range)\b/.test(t)) return 'both';
  return null;
};
/* Le biais du desk NQ ne vaut que s’il date d’aujourd’hui (heure de Paris). Une chaîne nue ne porte pas de date : ignorée. */
L.nqStamp = function (raw) { if (!raw || typeof raw !== 'object') return 0; return fin(raw.at) ? raw.at : fin(raw.t) ? raw.t : fin(raw.u) ? raw.u : fin(raw.ts) ? raw.ts : 0; };
L.parseBias = function (raw, today) {
  if (!raw || typeof raw !== 'object') return null;
  var d = raw.date || raw.day || raw.d || (L.nqStamp(raw) ? L.dayKeyOf(L.nqStamp(raw)) : null);
  if (d !== today) return null;
  var v = raw.bias != null ? raw.bias : raw.v != null ? raw.v : raw.value != null ? raw.value : raw.dir != null ? raw.dir : raw.side;
  return L.normDir(v);
};
/* Biais effectif : le plus récent du choix fait ici et du biais du desk NQ ; sans choix local, celui du desk NQ. */
L.effBias = function (plan, nqRaw, today) {
  var nq = L.parseBias(nqRaw, today), at = nq ? L.nqStamp(nqRaw) : 0;
  if (plan.dir && (!nq || plan.dirAt >= at)) return { dir: plan.dir, src: 'local', nq: nq };
  if (nq) return { dir: nq, src: 'nq', nq: nq };
  return { dir: null, src: null, nq: null };
};
L.nDone = function (plan, k) { return (plan.checks[k] || []).filter(Boolean).length; };
L.passed = function (plan, k, dir) { if (k === 'T' && !dir) return false; var c = plan.checks[k] || []; return c.length > 0 && c.every(Boolean); };
L.activeKey = function (plan, dir) { for (var i = 0; i < 3; i++) if (!L.passed(plan, L.STAGE_KEYS[i], dir)) return L.STAGE_KEYS[i]; return 'X'; };
function copyPlan(p) { return JSON.parse(JSON.stringify(p)); }
L.toggle = function (plan, k, i) { var p = copyPlan(plan); if (p.checks[k] && i >= 0 && i < p.checks[k].length) p.checks[k][i] = !p.checks[k][i]; return p; };
L.afterDecision = function (plan) { var p = copyPlan(plan); p.checks.B = p.checks.B.map(function () { return false; }); p.checks.P = p.checks.P.map(function () { return false; }); p.side = null; return p; };
L.newSession = function (plan) { var p = L.afterDecision(plan); p.checks.T = p.checks.T.map(function () { return false; }); p.dir = null; p.dirAt = 0; return p; };
L.setupText = function (sig) { return 'Bande VWAP · ' + (sig === 'absorption' ? 'Absorption' : 'Rejet'); };
/* Un refus ne porte ni sens ni mise (contrat du journal). */
L.refus = function (k, sig, at) { return { kind: 'refus', stage: L.STAGE_OF[k] || 'declencheur', at: at, setup: L.setupText(sig) }; };
L.sideOf = function (dir, side) { return dir === 'long' ? 'long' : dir === 'short' ? 'short' : (side === 'long' || side === 'short' ? side : null); };
L.draft = function (dir, side, sig) { var s = L.sideOf(dir, side); return s ? { kind: 'pris', side: s, setup: L.setupText(sig) } : null; };
L.tradeLabel = function (dir, side) {
  var s = L.sideOf(dir, side);
  if (s === 'long') return '▲ long à −2σ'; if (s === 'short') return '▼ short à +2σ';
  return dir === 'both' ? '⇅ selon la bande' : '';
};
L.biasWord = function (d) { return d === 'long' ? 'acheteur' : d === 'short' ? 'vendeur' : d === 'both' ? 'neutre' : null; };

/* ---------- 1.2 Le seuil µ* : port exact de calcFactory (plan-seance) ----------
   Fonction autonome : elle tourne telle quelle dans le Web Worker de T.compute et dans les tests. */
function microSeuil(p) {
  function calcFactory(){
    var PI=Math.PI, MAX_TERMS=200000, TOL=1e-15, PLAUS=[0.6,3.2];
    function nTerms(l,T,s){var lam1=Math.pow(PI*s/l,2)/2;var nExp=Math.sqrt(40/Math.max(lam1*T,1e-18));return Math.trunc(Math.min(MAX_TERMS,Math.max(40000,Math.ceil(nExp)+8)));}
    function absorption(a,b,T,mu,s){
      var l=a+b,v=s*s,theta=mu/v,nu=mu*mu/(2*v),alpha=PI*a/l,up=0,down=0,quiet=0,nMax=nTerms(l,T,s);
      for(var n=1;n<=nMax;n++){var lam=Math.pow(n*PI*s/l,2)/2,damp=lam+nu;var w=nu/damp+(lam/damp)*Math.exp(-damp*T);var base=(2/(n*PI))*Math.sin(n*alpha)*w;down+=base;up+=(n%2)?base:-base;if(Math.abs(base)<TOL){quiet++;if(quiet>24)break;}else quiet=0;}
      var pUp=Math.exp(theta*b)*(a/l-up),pDown=Math.exp(-theta*a)*(b/l-down);
      pUp=Math.min(Math.max(pUp,0),1);pDown=Math.min(Math.max(pDown,0),1);
      return [pUp,pDown,Math.max(0,1-pUp-pDown)];
    }
    function expectedExitTime(a,b,T,s){var l=a+b,alpha=PI*a/l,nMax=nTerms(l,T,s),total=0,quiet=0;for(var n=1;n<=nMax;n+=2){var lam=Math.pow(n*PI*s/l,2)/2;var term=(4/(n*PI))*Math.sin(n*alpha)*(1-Math.exp(-lam*T))/lam;total+=term;if(Math.abs(term)<TOL*Math.max(1,Math.abs(total))){quiet++;if(quiet>32)break;}else quiet=0;}return total;}
    function survival(a,b,T,s){var l=a+b,alpha=PI*a/l,nMax=nTerms(l,T,s),total=0,quiet=0;for(var n=1;n<=nMax;n+=2){var lam=Math.pow(n*PI*s/l,2)/2;var term=(4/(n*PI))*Math.sin(n*alpha)*Math.exp(-lam*T);total+=term;if(Math.abs(term)<TOL){quiet++;if(quiet>32)break;}else quiet=0;}return Math.min(1,Math.max(0,total));}
    function eff(T,H){return Math.pow(T,2*H);}
    function exposure(a,b,T,s,H){
      if(Math.abs(H-0.5)<1e-12) return expectedExitTime(a,b,T,s);
      var n=512,h=T/n,acc=0;
      for(var i=0;i<=n;i++){var t=i*h;var sv=t<=0?1:survival(a,b,eff(t,H),s);var w=(i===0||i===n)?1:(i%2?4:2);acc+=w*sv;}
      return acc*h/3;
    }
    function pTargetBeforeStop(a,b,mu,s){var theta=2*mu/(s*s);if(Math.abs(theta)<1e-12)return a/(a+b);var x=-theta*a,y=-theta*(a+b),num,den;if(y>0){num=Math.exp(-y)-Math.exp(x-y);den=Math.exp(-y)-1;}else{num=1-Math.exp(x);den=1-Math.exp(y);}if(Math.abs(den)<1e-300)return a/(a+b);return Math.max(0,Math.min(1,num/den));}
    function requiredDrift(a,b,s,c){
      function E(mu){var p=pTargetBeforeStop(a,b,mu,s);return p*(b-c)-(1-p)*(a+c);}
      if(b<=c)return Infinity;var lo=0,hi=Math.max(s,1e-6);
      for(var k=0;k<60;k++){if(E(hi)>=0)break;hi*=2;if(hi>1e9)return Infinity;}
      for(var j=0;j<200;j++){var mid=0.5*(lo+hi);if(E(mid)<0)lo=mid;else hi=mid;if(hi-lo<1e-12*Math.max(1,hi))break;}
      return 0.5*(lo+hi);
    }
    function normPpf(p){var A=[-3.969683028665376e01,2.209460984245205e02,-2.759285104469687e02,1.383577518672690e02,-3.066479806614716e01,2.506628277459239e00],B=[-5.447609879822406e01,1.615858368580409e02,-1.556989798598866e02,6.680131188771972e01,-1.328068155288572e01],C=[-7.784894002430293e-03,-3.223964580411365e-01,-2.400758277161838e00,-2.549732539343734e00,4.374664141464968e00,2.938163982698783e00],D=[7.784695709041462e-03,3.224671290700398e-01,2.445134137142996e00,3.754408661907416e00],pl=0.02425,ph=1-pl,q,r;
      if(p<pl){q=Math.sqrt(-2*Math.log(p));return (((((C[0]*q+C[1])*q+C[2])*q+C[3])*q+C[4])*q+C[5])/((((D[0]*q+D[1])*q+D[2])*q+D[3])*q+1);}
      if(p>ph){q=Math.sqrt(-2*Math.log(1-p));return -(((((C[0]*q+C[1])*q+C[2])*q+C[3])*q+C[4])*q+C[5])/((((D[0]*q+D[1])*q+D[2])*q+D[3])*q+1);}
      q=p-0.5;r=q*q;return (((((A[0]*r+A[1])*r+A[2])*r+A[3])*r+A[4])*r+A[5])*q/(((((B[0]*r+B[1])*r+B[2])*r+B[3])*r+B[4])*r+1);}
    function kl(p,q){var out=0,pairs=[[p,q],[1-p,1-q]];for(var i=0;i<2;i++){var x=pairs[i][0],y=pairs[i][1];if(x>0){if(y<=0)return Infinity;out+=x*Math.log(x/y);}}return out/Math.LN2;}
    function decisionsFor(rr,fr){var q=1/(rr+1),p=(1+fr)/(rr+1);var bits=p<1?kl(Math.min(p,1),q):Infinity;var za=normPpf(0.95),zb=normPpf(0.8),lam=Math.pow(za+zb,2);return {q:q,p:p,bits:bits,n:bits>0&&isFinite(bits)?lam/(2*bits*Math.LN2):Infinity};}
    function rrMax(a,s,T){var p=function(rr){return absorption(a,rr*a,T,0,s)[0];};var haut=60;if(p(haut)>=0.05)return haut;var lo=0.25,hi=haut;if(p(lo)<0.05)return lo;for(var i=0;i<48;i++){var mid=0.5*(lo+hi);if(p(mid)>=0.05)lo=mid;else hi=mid;}return 0.5*(lo+hi);}
    function ecartDir(h,s,T,d){var a=s*Math.sqrt(h),b=2*a,t=Math.max(T,h),mu=d/60;return 100*(absorption(a,b,t,mu,s)[0]-absorption(a,b,t,-mu,s)[0]);}
    var hCache={};
    function horizonOpt(s,T){var key=s+'|'+T;if(hCache[key])return hCache[key];var n=Math.round(2*T),pas=10,iBest=1,eBest=-Infinity,i,e;
      for(i=1;i<=n;i+=pas){e=ecartDir(T*i/n,s,T,PLAUS[1]);if(e>eBest){eBest=e;iBest=i;}}
      var best=[0,-Infinity];for(i=Math.max(1,iBest-pas);i<=Math.min(n,iBest+pas);i++){var t0=T*i/n;e=ecartDir(t0,s,T,PLAUS[1]);if(e>best[1])best=[t0,e];}
      hCache[key]={h:best[0],ecart:best[1]};return hCache[key];}
    var mCache={};
    function hMinFn(s,sS,T,c){var key=[s,sS,T,c].join('|');if(mCache[key])return mCache[key];var H=Math.log(sS/s)/Math.log(T),need=60*c/PLAUS[1];
      function E(h){var a=s*Math.sqrt(h);return exposure(a,2*a,T,s,H);}
      var lo=0.25,hi=T,res;if(E(hi)<need)res={h:null};else if(E(lo)>=need)res={h:lo};else{for(var i=0;i<40;i++){var mid=0.5*(lo+hi);if(E(mid)>=need)hi=mid;else lo=mid;if(hi-lo<0.01)break;}res={h:hi};}
      if(res.h!=null){var a=s*Math.sqrt(res.h);res.a=a;res.portee=2*a/(s*Math.sqrt(T));if(res.portee>1)res.h=null;}
      mCache[key]=res;return res;}
    function compute(p){
      var a=+p.a,rr=+p.rr,c=+p.c,s=+p.s1,sS=+p.sS,T=+p.T,d=+p.drift||0;
      if(!(a>0&&rr>0&&c>=0&&s>0&&sS>0&&T>1))return {err:'Paramètre manquant ou invalide.'};
      var b=rr*a,H=Math.log(sS/s)/Math.log(T);
      var expo=exposure(a,b,T,s,H);
      var mu=c/expo*60;
      var ends=absorption(a,b,T,0,s);
      var ecart=s*Math.sqrt(T),portee=b/ecart,fr=c/a,dec=decisionsFor(rr,fr);
      var payante=mu<=PLAUS[1],aPortee=portee<=1;
      var hopt=horizonOpt(s,T),hm=hMinFn(s,sS,T,c);
      return {a:a,b:b,H:H,expo:expo,mu:mu,muNB:requiredDrift(a,b,s,c)*60,pObj:ends[0],pStop:ends[1],pOpen:ends[2],ecartSeance:ecart,portee:portee,
        fr:fr,eqRate:dec.p,nullRate:dec.q,bits:dec.bits,N:dec.n,er0:-fr,erD:(d/60*expo-c)/a,caseMin:60*c/PLAUS[1],rrMax:rrMax(a,s,T),
        hOpt:hopt.h,ecartOpt:hopt.ecart,hMin:hm.h,aMin:hm.a,payante:payante,aPortee:aPortee,ok:payante&&aPortee,sous:mu<PLAUS[0]};
    }
    return {compute:compute};
  }
  return calcFactory().compute(p);
}
L.seuil = microSeuil;
L.PLAUS = [0.6, 3.2];
L.SESSIONS_PER_YEAR = 252;
L.PRESETS = {
  ref: { n: 'Réf. ALP', lab: 'Calibration du document : ES à 6 000, σ 1 min = 1,25 pt, σ séance = 60 pt, c = 0,33 pt. Les chiffres publiés ne valent que sur elle.', level: 6000, s1: 1.25, sS: 60, c: 0.33, T: 390 },
  nq: { n: 'NQ', lab: 'Contrat plein Nasdaq : c = 0,45 pt aller-retour (commission 4 $ + 1 tick de sortie). À vérifier chez ton courtier.', c: 0.45 },
  mnq: { n: 'MNQ', lab: 'Micro Nasdaq : c = 2,25 pt aller-retour, cinq fois le NQ à stop égal. À vérifier chez ton courtier.', c: 2.25 },
  moi: { n: 'Mes réglages', lab: '' }
};
L.PRESET_IDS = ['ref', 'nq', 'mnq', 'moi'];
/* Même construction que les préréglages NQ et MNQ : commission aller-retour convertie en points, plus un tick de sortie. */
L.frictionOf = function (set) { var s = set || {}; if (!(s.pointValue > 0) || !fin(s.commissionRT) || !fin(s.tick)) return NaN; return s.commissionRT / s.pointValue + s.tick; };
L.SEUIL0 = { preset: 'ref', level: 6000, s1: 1.25, sS: 60, c: 0.33, T: 390, a: 1.25 * Math.sqrt(15), rr: 2, drift: 0 };
L.normSeuil = function (raw) {
  var s = raw && typeof raw === 'object' ? raw : {}, o = {};
  Object.keys(L.SEUIL0).forEach(function (k) { o[k] = k === 'preset' ? (L.PRESET_IDS.indexOf(s.preset) >= 0 || s.preset === 'libre' ? s.preset : L.SEUIL0.preset) : (fin(s[k]) ? s[k] : L.SEUIL0[k]); });
  return o;
};
L.calcParams = function (s) { return { a: s.a, rr: s.rr, c: s.c, s1: s.s1, sS: s.sS, T: s.T, drift: s.drift }; };
L.applyPreset = function (s, key, set) {
  var o = Object.assign({}, s), P = L.PRESETS[key]; if (!P) return o;
  o.preset = key;
  if (key === 'moi') { var c = L.frictionOf(set); if (fin(c)) o.c = Math.round(c * 1e4) / 1e4; return o; }
  ['level', 's1', 'sS', 'c', 'T'].forEach(function (f) { if (P[f] != null) o[f] = P[f]; });
  return o;
};
L.applyGeo = function (s, pct) { var o = Object.assign({}, s); o.a = o.level * pct / 100; o.rr = 20; return o; };
L.applyHorizon = function (s, m) { var o = Object.assign({}, s); o.a = o.s1 * Math.sqrt(m); o.rr = 2; return o; };
L.caseMin = function (c) { return 60 * c / L.PLAUS[1]; };
L.verdict = function (c) {
  if (!c || c.err) return { code: 'err', pill: '—', tone: null, text: c && c.err ? c.err : 'Calcul en cours…' };
  if (c.ok) return { code: 'ok', pill: 'Négociable', tone: 'acc', text: 'Les deux conditions passent. ' + (c.sous ? 'µ* sous 0,6 pt/h : payante sous toute dérive plausible.' : 'µ* dans le domaine plausible.') };
  if (c.payante) return { code: 'portee', pill: 'Hors portée', tone: 'no', text: 'Payante, mais l’objectif est hors de portée de la séance (' + F.num(c.portee, 2) + ' σ).' };
  if (c.aPortee) return { code: 'domaine', pill: 'Hors domaine', tone: 'no', text: 'À portée, mais hors du domaine de dérive : µ* = ' + L.fmtMu(c.mu) + ' pt/h > 3,2.' };
  return { code: 'aucun', pill: 'Ni l’un ni l’autre', tone: 'no', text: 'Ni à portée ni dans le domaine.' };
};
L.fmtMu = function (v) { return fin(v) ? F.num(v, v < 10 ? 3 : 2) : (v === Infinity ? '∞' : '—'); };

/* ---------- 1.3 La grammaire du setup (ALP nº 3, partie III, tables 6 à 8) ---------- */
L.SEUILS = { volume: 1.5, z: 0.25, meche: 0.60, depassement: 1, delta: 1 / 3, fenetre: 15 };
L.NIVEAUX = [
  { k: 'poc', n: 'Point de contrôle', court: 'POC', fam: 'Profil de volume', calc: 'le pas du profil de la première demi-séance où le plus de volume s’est échangé', contacts: 2.14 },
  { k: 'va', n: 'Bord de valeur', court: 'Bord de valeur', fam: 'Profil de volume', calc: 'les deux bornes qui couvrent 70 % du volume de la première demi-séance, par extension depuis le point de contrôle', contacts: 3.89 },
  { k: 'lvn', n: 'Nœud de faible volume', court: 'Nœud faible vol.', fam: 'Profil de volume', calc: 'un creux local du profil de la première demi-séance, de proéminence 5 %', contacts: 11.54 },
  { k: 'vwap', n: 'Deuxième bande VWAP', court: 'Bande VWAP ±2σ', fam: 'Prix-volume', calc: 'le VWAP courant plus ou moins deux écarts-types courants, recalculés à chaque minute', contacts: 12.68 },
  { k: 'piv', n: 'Pivots de Dow', court: 'Pivots de Dow', fam: 'Structure de Dow', calc: 'les trois derniers sommets ou creux confirmés par un zigzag de 6 points, jamais lu à l’œil', contacts: 5.93 },
  { k: 'fib', n: 'Zone d’entrée 61,8–79 %', court: 'Zone 61,8–79 %', fam: 'Fibonacci', calc: 'le retracement de 61,8 % à 79 % de la dernière jambe du zigzag', contacts: 10.85 }
];
L.CONFS = [
  { k: 'abs', n: 'Absorption', idee: 'Un volume élevé s’échange et le prix ne bouge pas.', crit: [['Volume de la barre', '≥ 1,5 × la médiane'], ['z d’impact, en valeur absolue', '< 0,25'], ['Clôture', 'ne franchit pas le niveau']], inv: 'une clôture au-delà du niveau de plus d’1 σ d’une minute dans les 15 minutes' },
  { k: 'rej', n: 'Rejet', idee: 'Le prix sonde au-delà du niveau puis revient.', crit: [['Mèche au-delà du niveau', '≥ 60 % de l’étendue'], ['Clôture', 'revenue du côté d’origine']], inv: 'une clôture au-delà du niveau de plus d’1 σ d’une minute dans les 15 minutes' },
  { k: 'tra', n: 'Traversée', idee: 'Le prix franchit le niveau, porté par le flux.', crit: [['Clôture au-delà du niveau', '> 1 σ d’une minute'], ['Delta dans le sens', '≥ 33 % du volume']], inv: 'un retour du prix de l’autre côté du niveau dans les 15 minutes' }
];
/* Table 7 (mesure) et table 8 (prix de la confirmation), ligne à ligne. */
L.SETUPS = [
  { n: 'Absorption au point de contrôle', court: 'Abs. POC', niv: 'poc', conf: 'abs', fam: 'Profil de volume', contacts: 2.14, part: 2.3, obs: 44, dementie: 71.1, pBrut: 51.7, pConf: 47.7, mfe: 4.93, mae: -6.26, hz: '1 h', N: 13581, cAn: 540, confAn: 13, sans: 25.1, avec: 1078, facteur: 42.9, muComp: 1.07, verdictPub: 'il faut une dérive haute' },
  { n: 'Traversée du point de contrôle', court: 'Trav. POC', niv: 'poc', conf: 'tra', fam: 'Profil de volume', contacts: 2.14, part: 7.3, obs: 128, dementie: 60.3, pBrut: 48.3, pConf: 41.4, mfe: 4.90, mae: -6.50, hz: '1 h', N: 13581, cAn: 540, confAn: 39, sans: 25.1, avec: 344, facteur: 13.7, muComp: 0.61, verdictPub: 'il faut une dérive haute' },
  { n: 'Rejet du bord de valeur', court: 'Rejet bord VA', niv: 'va', conf: 'rej', fam: 'Profil de volume', contacts: 3.89, part: 9.9, obs: 311, dementie: 53.0, pBrut: 48.9, pConf: 48.9, mfe: 5.83, mae: -4.98, hz: '1 h', N: 13581, cAn: 981, confAn: 97, sans: 13.8, avec: 140, facteur: 10.1, muComp: 0.52, verdictPub: 'une dérive ordinaire suffit' },
  { n: 'Acceptation hors de la valeur', court: 'Accept. hors VA', niv: 'va', conf: 'tra', fam: 'Profil de volume', contacts: 3.89, part: 6.5, obs: 208, dementie: 61.8, pBrut: 51.1, pConf: 48.1, mfe: 6.45, mae: -5.88, hz: '1 h', N: 13581, cAn: 981, confAn: 64, sans: 13.8, avec: 213, facteur: 15.4, muComp: 0.64, verdictPub: 'il faut une dérive haute' },
  { n: 'Traversée d’un nœud de faible volume', court: 'Trav. NFV', niv: 'lvn', conf: 'tra', fam: 'Profil de volume', contacts: 11.54, part: 6.5, obs: 518, dementie: 59.8, pBrut: 48.5, pConf: 51.9, mfe: 5.75, mae: -5.12, hz: '1 h', N: 13581, cAn: 2909, confAn: 190, sans: 4.7, avec: 71.6, facteur: 15.3, muComp: 0.64, verdictPub: 'il faut une dérive haute' },
  { n: 'Rejet d’un nœud de faible volume', court: 'Rejet NFV', niv: 'lvn', conf: 'rej', fam: 'Profil de volume', contacts: 11.54, part: 10.5, obs: 745, dementie: 55.4, pBrut: 51.5, pConf: 49.7, mfe: 5.90, mae: -6.14, hz: '1 h', N: 13581, cAn: 2909, confAn: 304, sans: 4.7, avec: 44.6, facteur: 9.6, muComp: 0.51, verdictPub: 'une dérive ordinaire suffit' },
  { n: 'Rejet de la deuxième bande', court: 'Rejet bande 2σ', niv: 'vwap', conf: 'rej', fam: 'Prix-volume', contacts: 12.68, part: 11.1, obs: 832, dementie: 57.5, pBrut: 48.7, pConf: 50.1, mfe: 4.13, mae: -3.88, hz: '30 min', N: 6803, cAn: 3195, confAn: 356, sans: 2.1, avec: 19.1, facteur: 9.0, muComp: 0.98, verdictPub: 'il faut une dérive haute' },
  { n: 'Sortie de bande', court: 'Sortie de bande', niv: 'vwap', conf: 'tra', fam: 'Prix-volume', contacts: 12.68, part: 7.1, obs: 632, dementie: 61.2, pBrut: 51.3, pConf: 49.7, mfe: 3.97, mae: -4.26, hz: '30 min', N: 6803, cAn: 3195, confAn: 226, sans: 2.1, avec: 30.1, facteur: 14.2, muComp: 1.23, verdictPub: 'il faut une dérive haute' },
  { n: 'Retest de pivot tenu', court: 'Retest pivot', niv: 'piv', conf: 'rej', fam: 'Structure de Dow', contacts: 5.93, part: 11.1, obs: 472, dementie: 60.3, pBrut: 49.1, pConf: 42.8, mfe: 6.17, mae: -7.87, hz: '2 h', N: 27123, cAn: 1494, confAn: 165, sans: 18.2, avec: 164, facteur: 9.0, muComp: 0.25, verdictPub: 'une dérive ordinaire suffit' },
  { n: 'Rupture de structure', court: 'Rupture', niv: 'piv', conf: 'tra', fam: 'Structure de Dow', contacts: 5.93, part: 5.9, obs: 279, dementie: 61.7, pBrut: 50.9, pConf: 48.7, mfe: 6.86, mae: -7.25, hz: '2 h', N: 27123, cAn: 1494, confAn: 88, sans: 18.2, avec: 309, facteur: 17.0, muComp: 0.34, verdictPub: 'une dérive ordinaire suffit' },
  { n: 'Absorption en zone d’entrée', court: 'Abs. 61,8–79', niv: 'fib', conf: 'abs', fam: 'Fibonacci', contacts: 10.85, part: 1.8, obs: 171, dementie: 58.3, pBrut: 47.4, pConf: 45.6, mfe: 4.61, mae: -6.02, hz: '45 min', N: 10193, cAn: 2734, confAn: 50, sans: 3.7, avec: 202, facteur: 54.3, muComp: 1.61, verdictPub: 'il faut une dérive haute' },
  { n: 'Rejet en zone d’entrée', court: 'Rejet 61,8–79', niv: 'fib', conf: 'rej', fam: 'Fibonacci', contacts: 10.85, part: 8.9, obs: 703, dementie: 54.2, pBrut: 47.4, pConf: 49.1, mfe: 5.64, mae: -4.69, hz: '45 min', N: 10193, cAn: 2734, confAn: 245, sans: 3.7, avec: 41.7, facteur: 11.2, muComp: 0.73, verdictPub: 'il faut une dérive haute' }
];
L.POOL = { obs: 5043, contacts: 20874, pBrut: 49.4, pConf: 48.7, demi: 1.4, rapport: 1.00, seances: 900 };
/* Le verdict est calculé, jamais écrit : la dérive compensatrice comparée au domaine plausible (alp1/setups.py). */
L.verdictSetup = function (mu) { if (!fin(mu)) return '—'; if (mu <= L.PLAUS[0]) return 'une dérive ordinaire suffit'; if (mu <= L.PLAUS[1]) return 'il faut une dérive haute'; return 'hors du domaine : irremboursable'; };
L.fmtAns = function (y) { return fin(y) ? F.num(y, y < 100 ? 1 : 0, 'ans') : '—'; };

/* ---------- 1.4 Le catalogue des quinze lectures (ALP nº 3, partie III, tables 2, 3, 5) ---------- */
L.SEANCE_MIN = 390;
L.minutes = function (hz) {
  var m = /^([\d,]+)\s*(min|h|séances?)$/.exec(String(hz || '').trim()); if (!m) return NaN;
  var v = parseFloat(m[1].replace(',', '.'));
  return m[2] === 'min' ? v : m[2] === 'h' ? v * 60 : v * L.SEANCE_MIN;
};
L.LECTURES = [
  { n: 1, nom: 'Absorption', fam: 'Footprint', hz: '5 min', occ: 78.00, freq: 19.7, loi: 'loi centrale du z d’impact', sit: 'un volume élevé s’échange et le prix ne bouge pas', att: 'le rejet du côté où le volume a été absorbé', depH: 0.27, gain: 3.9, a: 2.80, req: 37.27, mu: 1.947, N: 1144, an: 3880, delai: [3.5, 'mois'], muN: 2226 },
  { n: 2, nom: 'Déséquilibre diagonal', fam: 'Footprint', hz: '5 min', occ: 624.00, freq: 11.7, loi: 'binomiale exacte, à taille de grappe déclarée', sit: 'l’ask d’un niveau écrase le bid du niveau du dessous, trois pour un', att: 'la poursuite du mouvement dans le sens du déséquilibre', depH: 0.27, gain: 3.9, a: 2.80, req: 37.27, mu: 1.947, N: 1144, an: 18409, delai: [0.7, 'mois'], muN: 2226 },
  { n: 3, nom: 'Persistance de liquidité', fam: 'Carnet', hz: '5 min', occ: 48.00, freq: 40.7, loi: 'loi exponentielle du retrait', sit: 'un bloc affiché reste en place au lieu de se retirer', att: 'le niveau tient et le prix rebondit dessus', depH: 0.27, gain: 3.9, a: 2.80, req: 37.27, mu: 1.947, N: 1144, an: 4918, delai: [2.8, 'mois'], muN: 2226 },
  { n: 4, nom: 'Épuisement', fam: 'Footprint', hz: '5 min', occ: 78.00, freq: 7.0, loi: 'loi simulée du rapport d’épuisement', sit: 'le volume s’effondre au niveau extrême de l’excursion', att: 'le retournement, faute de participants au bout', depH: 0.27, gain: 3.9, a: 2.80, req: 37.27, mu: 1.947, N: 1144, an: 1375, delai: [10.0, 'mois'], muN: 2226 },
  { n: 5, nom: 'Divergence du CVD', fam: 'Flux', hz: '15 min', occ: 26.00, freq: 28.7, loi: 'loi du signe sous corrélation déclarée', sit: 'le prix fait un nouvel extrême, le volume delta cumulé non', att: 'l’essoufflement puis le retournement', depH: 0.80, gain: 6.5, a: 4.84, req: 35.61, mu: 0.653, N: 3411, an: 1881, delai: [1.8, 'ans'], muN: 2228 },
  { n: 6, nom: 'Bande VWAP', fam: 'Prix-volume', hz: '30 min', occ: 9.05, freq: 12.4, loi: 'détecteur simulé sur séances sans dérive', sit: 'le prix touche la deuxième bande d’écart-type autour du VWAP', att: 'le retour vers le VWAP', depH: 1.60, gain: 8.8, a: 6.85, req: 34.94, mu: 0.328, N: 6803, an: 282, delai: [24.2, 'ans'], muN: 2228 },
  { n: 7, nom: 'Zone d’entrée optimale', fam: 'Fibonacci', hz: '45 min', occ: 6.00, freq: 13.9, loi: 'loi de retracement sous martingale', sit: 'le prix retrace une jambe entre 61,8 % et 79 %', att: 'la reprise de la jambe depuis la zone', depH: 2.40, gain: 11.3, a: 8.39, req: 34.65, mu: 0.219, N: 10193, an: 211, delai: [48.4, 'ans'], muN: 2228 },
  { n: 8, nom: 'Nœud de faible volume', fam: 'Prix-volume', hz: '1 h', occ: 8.97, freq: 71.8, loi: 'détecteur simulé sur séances sans dérive', sit: 'le prix aborde une zone où peu de volume s’est échangé', att: 'la traversée rapide, faute de liquidité pour retenir', depH: 3.20, gain: 12.9, a: 9.68, req: 34.47, mu: 0.164, N: 13581, an: 1623, delai: [8.4, 'ans'], muN: 2229 },
  { n: 9, nom: 'Retour au point de contrôle', fam: 'Prix-volume', hz: '1 h', occ: 0.89, freq: 63.6, loi: 'détecteur simulé sur séances sans dérive', sit: 'le prix s’écarte du prix le plus échangé de la séance', att: 'le retour au point de contrôle avant la clôture', depH: 3.20, gain: 12.9, a: 9.68, req: 34.47, mu: 0.164, N: 13581, an: 142, delai: [95.8, 'ans'], muN: 2229 },
  { n: 10, nom: 'Tirages simples', fam: 'Profil de marché', hz: '1,5 h', occ: 8.93, freq: 50.3, loi: 'loi simulée du profil TPO', sit: 'une rangée du profil n’est visitée que par une seule période', att: 'le comblement de la rangée laissée vide', depH: 4.80, gain: 15.8, a: 11.86, req: 34.26, mu: 0.110, N: 20353, an: 1132, delai: [18.0, 'ans'], muN: 2229 },
  { n: 11, nom: 'Retest de niveau', fam: 'Structure', hz: '2 h', occ: 1.02, freq: 13.9, loi: 'détecteur simulé sur séances sans dérive', sit: 'le prix revient sur un extrême de séance qu’il avait quitté', att: 'le niveau tient et le prix repart', depH: 6.40, gain: 17.8, a: 13.69, req: 34.14, mu: 0.082, N: 27123, an: 36, delai: [755, 'ans'], muN: 2229 },
  { n: 12, nom: 'Extrême pauvre', fam: 'Profil de marché', hz: '1 séance', occ: 1.00, freq: 3.2, loi: 'loi simulée du profil TPO', sit: 'le haut de séance est plat, sans queue de rejet', att: 'l’extension au-delà, la séance suivante', depH: 20.80, gain: 29.9, a: 24.69, req: 33.78, mu: 0.025, N: 88014, an: 8, delai: [11.0, 'millénaires'], muN: 2229 },
  { n: 13, nom: 'Rejet en mèche', fam: 'Structure', hz: '1 séance', occ: 1.00, freq: 33.3, loi: 'loi de la mèche dominante sous martingale', sit: 'la bougie de séance ferme loin de son extrême, mèche dominante', att: 'le rejet du niveau touché par la mèche', depH: 20.80, gain: 29.9, a: 24.69, req: 33.78, mu: 0.025, N: 88014, an: 84, delai: [1048, 'ans'], muN: 2229 },
  { n: 14, nom: 'Régime de gamma', fam: 'Dérivés', hz: '1 séance', occ: 1.00, freq: 48.5, loi: 'détecteur simulé sur séances sans dérive', sit: 'l’exposition gamma des teneurs de marché passe sous zéro', att: 'l’amplification des mouvements au lieu de leur amortissement', depH: 20.80, gain: 29.9, a: 24.69, req: 33.78, mu: 0.025, N: 88014, an: 122, delai: [720, 'ans'], muN: 2229 },
  { n: 15, nom: 'Plus haut plus haut', fam: 'Structure', hz: '3 séances', occ: 0.34, freq: 88.2, loi: 'loi du plus haut plus haut sous martingale', sit: 'trois séances dessinent un sommet plus haut et un creux plus haut', att: 'la poursuite de la tendance ainsi établie', depH: 62.40, gain: 43.8, a: 42.76, req: 33.59, mu: 0.008, N: 263824, an: 76, delai: [3490, 'ans'], muN: 2230 }
];
L.TAUX_NUL = 100 / 3;
L.CARRIERE = 30;
/* L’ordre n’est pas écrit : il est celui de l’horizon, converti en minutes (une séance = 390 min). Tri stable. */
L.ordre = function () {
  return L.LECTURES.map(function (x, i) { return { x: x, i: i, m: L.minutes(x.hz) }; })
    .sort(function (p, q) { return p.m - q.m || p.i - q.i; })
    .map(function (p, r) { return Object.assign({}, p.x, { rang: r + 1, minutes: p.m }); });
};
L.annees = function (d) { if (!d || !fin(d[0])) return NaN; return d[1] === 'mois' ? d[0] / 12 : d[1] === 'millénaires' ? d[0] * 1000 : d[0]; };
L.fmtDelai = function (d) {
  if (!d || !fin(d[0])) return '—';
  if (d[1] === 'mois' || d[1] === 'millénaires') return F.num(d[0], 1, d[1]);
  return F.num(d[0], d[0] < 100 ? 1 : 0, 'ans');
};
L.etablissables = function () { return L.LECTURES.filter(function (x) { return L.annees(x.delai) < L.CARRIERE; }).length; };
L.familles = function () { var o = []; L.LECTURES.forEach(function (x) { if (o.indexOf(x.fam) < 0) o.push(x.fam); }); return o; };

/* =====================================================================
   2. Rendu
   ===================================================================== */
var CSS = [
  '.mi-canvas{position:relative;display:flex;flex-direction:column;align-items:center;gap:30px;padding:2px 0 4px}',
  '.mi-canvas>svg{position:absolute;left:0;top:0;pointer-events:none;overflow:visible}',
  '.mi-node{position:relative;z-index:1;border:1px solid var(--line);border-radius:12px;background:var(--panel);padding:11px 12px 12px;display:flex;flex-direction:column;gap:10px;min-width:0;max-width:100%;transition:border-color .2s}',
  '.mi-node[data-s="active"]{border-color:var(--violet);box-shadow:0 0 0 1px var(--violet)}',
  '.mi-node[data-s="done"]{border-color:var(--line-2)}',
  '.mi-nh{display:flex;align-items:center;gap:9px;min-width:0}',
  '.mi-ix{width:28px;height:28px;border-radius:8px;border:1px solid var(--line-2);display:grid;place-items:center;font:600 11px/1 var(--f-mono);color:var(--soft);flex:none}',
  '.mi-node[data-s="done"] .mi-ix{background:var(--hi);border-color:var(--hi);color:var(--ink)}',
  '.mi-node[data-s="active"] .mi-ix{background:var(--violet);border-color:var(--violet);color:var(--ink)}',
  '.mi-nh b{flex:1;min-width:0;font-size:14.5px;font-weight:600;color:var(--hi);line-height:1.2}',
  '.mi-node[data-s="wait"] .mi-nh b{color:var(--soft)}',
  '.mi-ct{font:600 11px/1 var(--f-mono);color:var(--mute);flex:none}',
  '.mi-sub{margin:0;font-size:12.5px;color:var(--mute);line-height:1.45;display:flex;flex-wrap:wrap;gap:6px 8px;align-items:center}',
  '.mi-k5{font-family:var(--f-serif);font-style:italic;font-size:15.5px;line-height:1.35;color:var(--violet-2)}',
  '.mi-node .checks{border-radius:9px;background:var(--bg)}',
  '.mi-node .ck{padding:10px 11px}',
  '.mi-src{font:500 10.5px/1.35 var(--f-mono);color:var(--mute)}',
  '.mi-rules p{margin:0 0 6px;font-size:13px;color:var(--soft);line-height:1.5}',
  '.mi-rules p:last-child{margin-bottom:0}',
  '.mi-rules b{color:var(--fg);font-weight:600}',
  '.mi-take{display:grid;grid-template-columns:1fr 1fr;gap:8px}',
  '.mi-w{fill:none;stroke:var(--line-2);stroke-width:1.3}',
  '.mi-w.on{stroke:var(--violet);stroke-width:1.5}',
  '.mi-w.go{stroke:var(--violet);stroke-dasharray:3 5;animation:flow .9s linear infinite}',
  '.mi-fun{fill:none;stroke:var(--line-2);stroke-width:1;stroke-dasharray:2 5;opacity:.7}',
  '.mi-pt{fill:var(--bg);stroke:var(--line-2);stroke-width:1.3}',
  '.mi-pt.on{fill:var(--violet);stroke:var(--violet)}',
  '.mi-tg{font:600 9.5px/1 var(--f-mono);letter-spacing:.08em;fill:var(--mute)}',
  '.mi-tg.on{fill:var(--violet-2)}',
  '.mi-bar{display:flex;height:12px;border-radius:4px;overflow:hidden;border:1px solid var(--line-2);background:var(--raise)}',
  '.mi-bar i{display:block;height:100%}',
  '.mi-bar i.o{background:var(--violet)} .mi-bar i.s{background:var(--soft)} .mi-bar i.c{background-image:var(--hatch);background-color:var(--raise-2)}',
  '.mi-lg{display:flex;flex-wrap:wrap;gap:6px 14px;font:500 11px/1.3 var(--f-mono);color:var(--soft)}',
  '.mi-lg span{display:inline-flex;align-items:center;gap:6px}',
  '.mi-lg i{width:10px;height:10px;border-radius:2px;display:inline-block;border:1px solid var(--line-2)}',
  '.mi-lg i.o{background:var(--violet);border-color:var(--violet)} .mi-lg i.s{background:var(--soft)} .mi-lg i.c{background-image:var(--hatch);background-color:var(--raise-2)}',
  '.mi-cond{display:flex;align-items:center;gap:10px;justify-content:space-between;padding:9px 0;border-top:1px solid var(--line)}',
  '.mi-cond:first-child{border-top:0;padding-top:0}',
  '.mi-cond div{min-width:0}',
  '.mi-cond b{display:block;font-size:13px;color:var(--fg);font-weight:600}',
  '.mi-cond span{display:block;font:500 11px/1.35 var(--f-mono);color:var(--mute)}',
  '.mi-vt{font-size:13.5px;color:var(--fg);line-height:1.5;margin:0}',
  '.mi-crit{display:flex;flex-direction:column;border:1px solid var(--line);border-radius:9px;overflow:hidden}',
  '.mi-crit>div{display:flex;justify-content:space-between;align-items:baseline;gap:10px;padding:8px 10px;border-top:1px solid var(--line);font-size:12.5px;color:var(--soft)}',
  '.mi-crit>div:first-child{border-top:0}',
  '.mi-crit>div b{font:600 12px/1.3 var(--f-mono);color:var(--hi);text-align:right}',
  '.mi-inv{font-size:12.5px;color:var(--mute);margin:0;line-height:1.45}',
  '.mi-inv b{color:var(--soft);font-weight:600}',
  '.mi-def{display:flex;flex-direction:column;gap:2px;padding:10px 0;border-top:1px solid var(--line)}',
  '.mi-def:first-child{border-top:0;padding-top:0}',
  '.mi-def>div{display:flex;justify-content:space-between;gap:10px;align-items:baseline}',
  '.mi-def b{font-size:13.5px;color:var(--fg);font-weight:600}',
  '.mi-def em{font:500 10.5px/1 var(--f-mono);font-style:normal;color:var(--mute);white-space:nowrap}',
  '.mi-def p{margin:0;font-size:12.5px;color:var(--mute);line-height:1.45}',
  '.mi-fi{display:flex;flex-direction:column;gap:8px}',
  '.mi-fi p{margin:0;font-size:13.5px;color:var(--soft);line-height:1.5}',
  '.mi-fi p b{color:var(--fg);font-weight:600}'
].join('\n');
function injectCss() { if (document.getElementById('micro-css')) return; var s = document.createElement('style'); s.id = 'micro-css'; s.textContent = CSS; document.head.appendChild(s); }
function typo(el) {
  if (!el || typeof document === 'undefined') return;
  var w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, { acceptNode: function (n) { var p = n.parentNode; return p && /^(TEXTAREA|SCRIPT|STYLE|INPUT|OPTION)$/.test(p.nodeName) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT; } }), n;
  while ((n = w.nextNode())) { var t = n.nodeValue, u = T.typo(t); if (u !== t) n.nodeValue = u; }
}
var UI = { focus: null, lect: null, req: 0, cache: {} };
var X = T.esc;
function pc1(v) { return fin(v) ? F.num(v, 1, '%') : '—'; }

/* ---------- 2.1 Plan ---------- */
function todayRows() { var k = T.day.key(); return T.journal.list().filter(function (r) { return L.dayKeyOf(r.at) === k; }); }
function loadPlan() { return L.normPlan(T.store.get(K.plan, null), T.day.key()); }
function savePlan(p) { T.store.set(K.plan, p); }

function renderPlan(root, ctx) {
  var set = ctx.settings, today = T.day.key(), plan = loadPlan(), nqRaw = T.store.get(K.nqBias, null), eb = L.effBias(plan, nqRaw, today), dir = eb.dir;
  var stages = L.stages(set), act = L.activeKey(plan, dir), kid = plan.kid, win = T.time.inWindow(set.winFrom, set.winTo, set.tz), w = L.window(set);
  var rows = todayRows(), nP = rows.filter(function (r) { return r.kind === 'pris'; }).length, nR = rows.filter(function (r) { return r.kind === 'refus'; }).length;
  var actSt = stages.find(function (s) { return s.k === act; });

  root.appendChild(U.kpis([
    { label: 'Biais du jour', value: L.biasWord(dir) || 'à choisir', tone: dir ? 'acc' : null, hint: eb.src === 'nq' ? 'lu au desk NQ' : eb.src === 'local' ? 'déclaré ici' : 'étape 1' },
    { label: 'Fenêtre ' + pad2(w.from) + '–' + pad2(w.to) + ' h', value: win ? 'ouverte' : 'fermée', tone: win ? 'acc' : null, hint: 'heure de Paris ' + T.time.hhmm('Europe/Paris') },
    { label: 'Étape active', value: act === 'X' ? 'Trade' : { T: 'Tendance', B: 'VWAP', P: 'Déclencheur' }[act], hint: act === 'X' ? 'trois filtres passés' : L.nDone(plan, act) + ' / ' + actSt.items.length + ' conditions' },
    { label: 'Aujourd’hui', value: nP + ' · ' + nR, hint: 'pris · refus au journal' }
  ], 4));

  var s1 = U.section('Le plan, *étape par étape*', '3 étapes · ' + stages.reduce(function (a, s) { return a + s.items.length; }, 0) + ' conditions');
  s1.appendChild(U.seg({ aria: 'Version des explications', options: [{ v: 'n', label: 'Explication' }, { v: 'k', label: 'Version 5 ans' }], value: kid ? 'k' : 'n', onChange: function (v) { var p = loadPlan(); p.kid = v === 'k'; savePlan(p); ctx.rerender(); } }));
  s1.appendChild(canvas(plan, stages, eb, act, win, set, ctx));
  s1.appendChild(U.note(kid ? L.FOOT.k : L.FOOT.n));
  s1.appendChild(h('div', { class: 'row' }, U.button({ label: 'Nouvelle séance', kind: 'ghost', small: true, onClick: function () { savePlan(L.newSession(loadPlan())); T.toast('Nouvelle séance · étape 1 à refaire'); window.scrollTo({ top: 0, behavior: 'smooth' }); ctx.rerender(); } }), h('span', { class: 'mi-src' }, 'Les coches se remettent à zéro chaque jour, heure de Paris.')));
  root.appendChild(s1);

  if (UI.focus) {
    var fk = UI.focus; UI.focus = null;
    requestAnimationFrame(function () { var el = root.querySelector('[data-node="' + fk + '"]'); if (el && el.scrollIntoView) el.scrollIntoView({ behavior: 'smooth', block: 'center' }); });
  }
  var un1 = T.journal.on(function () { ctx.rerender(); }), un2 = T.store.on(K.nqBias, function () { ctx.rerender(); });
  var tick = setInterval(function () { if (document.visibilityState === 'visible') ctx.rerender(); }, 60000);
  return function () { un1(); un2(); clearInterval(tick); };
}

var WIDTHS = { T: 100, B: 91, P: 82, X: 73 };
function canvas(plan, stages, eb, act, win, set, ctx) {
  var dir = eb.dir, kid = plan.kid, wrap = h('div', { class: 'mi-canvas' }), svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('aria-hidden', 'true'); wrap.appendChild(svg);
  var order = ['T', 'B', 'P', 'X'];

  function toggle(k, i) {
    var before = L.activeKey(loadPlan(), dir), p = L.toggle(loadPlan(), k, i); savePlan(p);
    var after = L.activeKey(p, dir), d = T.day.get().done;
    if (L.passed(p, 'T', dir) && !d.biais) T.day.mark('biais');
    if (L.passed(p, 'B', dir) && !d.fenetre) T.day.mark('fenetre');
    if (L.passed(p, 'P', dir) && !d.declencheur) T.day.mark('declencheur');
    if (after !== before && order.indexOf(after) > order.indexOf(before)) { UI.focus = after; T.toast(after === 'X' ? 'Les trois étapes sont faites' : 'Étape ' + L.STAGE_NAME[before] + ' faite'); }
    ctx.rerender();
  }
  function refuse(k) {
    var p = loadPlan(); savePlan(L.afterDecision(p));
    T.journal.add(L.refus(k, p.sig, Date.now()));
    UI.focus = 'B'; T.toast('Refus inscrit · filtré en ' + L.STAGE_NAME[k === 'X' ? 'P' : k]);
    ctx.rerender();
  }
  function take() {
    var p = loadPlan(), dr = L.draft(dir, p.side, p.sig); if (!dr) { T.toast('Choisis le sens avant de prendre le trade'); return; }
    T.store.set(K.draft, dr); savePlan(L.afterDecision(p));
    T.toast('Brouillon envoyé au journal'); T.nav.go('journal', 'saisir');
  }
  function setDir(d) { var p = loadPlan(); if (eb.src === 'local' && p.dir === d) { p.dir = null; p.dirAt = Date.now(); } else { p.dir = d; p.dirAt = Date.now(); } p.side = null; savePlan(p); ctx.rerender(); }

  stages.forEach(function (st, ix) {
    var k = st.k, s = L.passed(plan, k, dir) ? 'done' : act === k ? 'active' : 'wait';
    var node = h('article', { class: 'mi-node', 'data-node': k, 'data-s': s, style: 'width:' + WIDTHS[k] + '%' });
    node.appendChild(h('div', { class: 'mi-nh' }, h('span', { class: 'mi-ix' }, '0' + (ix + 1)), h('b', null, st.title), h('span', { class: 'mi-ct' }, L.nDone(plan, k) + '/' + st.items.length),
      U.button({ label: 'Pas pris', kind: 'ghost', small: true, aria: 'Pas pris : setup arrêté à l’étape ' + st.title, onClick: function () { refuse(k); } })));
    node.appendChild(h('p', { class: 'mi-sub' + (kid ? ' mi-k5' : '') }, kid ? st.k5 : st.sub, st.win && !kid ? U.pill(win ? 'ouverte' : 'fermée', win ? 'acc' : null) : null));
    if (k === 'T') {
      node.appendChild(U.seg({ aria: 'Biais du jour', options: [{ v: 'long', label: '▲ acheteur' }, { v: 'both', label: '⇅ neutre' }, { v: 'short', label: '▼ vendeur' }], value: dir, onChange: setDir }));
      var bn = eb.src === 'nq' ? 'Biais lu au desk NQ aujourd’hui. Toucher un autre biais le remplace ici.' : eb.src === 'local' && eb.nq && eb.nq !== dir ? 'Le desk NQ dit « ' + L.biasWord(eb.nq) + ' » ; ton choix d’ici, plus récent, prévaut.' : !dir ? 'Sans biais déclaré, l’étape 1 ne passe pas.' : null;
      if (bn) node.appendChild(h('span', { class: 'mi-src' }, bn));
    }
    if (k === 'P') node.appendChild(U.seg({ aria: 'Signal écrit d’avance', options: L.SIGNALS, value: plan.sig, onChange: function (v) { var p = loadPlan(); p.sig = v; savePlan(p); ctx.rerender(); } }));
    var checked = {}; (plan.checks[k] || []).forEach(function (on, i) { if (on) checked[k + i] = true; });
    node.appendChild(U.checklist({ items: st.items.map(function (it, i) { return { id: k + i, t: it.t, s: kid ? it.k : (it.dyn === 'vwap' ? L.vwapSub(dir) : it.s) }; }), checked: checked, onToggle: function (id) { toggle(k, +id.slice(1)); } }));
    wrap.appendChild(node);
  });

  var ok = act === 'X', side = L.sideOf(dir, plan.side), lab = L.tradeLabel(dir, plan.side);
  var tn = h('article', { class: 'mi-node', 'data-node': 'X', 'data-s': ok ? 'active' : 'wait', style: 'width:' + WIDTHS.X + '%' });
  tn.appendChild(h('div', { class: 'mi-nh' }, h('span', { class: 'mi-ix' }, '→'), h('b', null, 'Trade' + (lab ? ' · ' + lab : ''))));
  tn.appendChild(kid ? h('p', { class: 'mi-sub mi-k5' }, L.TRADE.k5) : h('div', { class: 'mi-rules' }, L.TRADE.rules(set).map(function (r) { return h('p', null, h('b', null, r[0]), ' ' + r[1]); })));
  if (dir === 'both') tn.appendChild(U.seg({ aria: 'Sens du trade', options: [{ v: 'long', label: '▲ long à −2σ' }, { v: 'short', label: '▼ short à +2σ' }], value: plan.side, onChange: function (v) { var p = loadPlan(); p.side = p.side === v ? null : v; savePlan(p); ctx.rerender(); } }));
  tn.appendChild(h('div', { class: 'mi-take' }, U.button({ label: 'Pris', kind: 'pri', disabled: !(ok && side), onClick: take }), U.button({ label: 'Pas pris', disabled: !ok, onClick: function () { refuse('X'); } })));
  if (ok && !side) tn.appendChild(h('span', { class: 'mi-src' }, 'Biais neutre : choisis le côté de la bande touchée.'));
  wrap.appendChild(tn);

  function draw() {
    if (!wrap.isConnected) return;
    var wr = wrap.getBoundingClientRect(), R = {}, out = '';
    svg.setAttribute('width', wr.width); svg.setAttribute('height', wr.height);
    order.forEach(function (k) { var el = wrap.querySelector('[data-node="' + k + '"]'); if (!el) return; var r = el.getBoundingClientRect(); R[k] = { l: r.left - wr.left, r: r.right - wr.left, t: r.top - wr.top, b: r.bottom - wr.top }; });
    if (R.X) {
      out += '<path class="mi-fun" d="M' + order.map(function (k) { return (R[k].l - 6).toFixed(1) + ',' + ((R[k].t + R[k].b) / 2).toFixed(1); }).join(' L') + '"/>';
      out += '<path class="mi-fun" d="M' + order.map(function (k) { return (R[k].r + 6).toFixed(1) + ',' + ((R[k].t + R[k].b) / 2).toFixed(1); }).join(' L') + '"/>';
    }
    for (var i = 0; i < order.length - 1; i++) {
      var a = order[i], b = order[i + 1]; if (!R[a] || !R[b]) continue;
      var x = (R[a].l + R[a].r) / 2, y1 = R[a].b, y2 = R[b].t, on = L.passed(plan, a, dir), go = on && act === b;
      out += '<path class="mi-w' + (go ? ' go' : on ? ' on' : '') + '" d="M' + x + ',' + y1 + ' L' + x + ',' + y2 + '"/>';
      out += '<circle class="mi-pt' + (on ? ' on' : '') + '" cx="' + x + '" cy="' + y1 + '" r="3"/><circle class="mi-pt' + (on ? ' on' : '') + '" cx="' + x + '" cy="' + y2 + '" r="3"/>';
      out += '<text class="mi-tg' + (on ? ' on' : '') + '" x="' + (x + 10) + '" y="' + ((y1 + y2) / 2 + 3.5) + '">' + (on ? 'PASSE' : 'FILTRE') + '</text>';
    }
    svg.innerHTML = out;
  }
  T.observe(wrap, draw);
  return wrap;
}

/* ---------- 2.2 Setups ---------- */
/* Graphique en rangées : un segment de a à b par ligne, échelle linéaire ou logarithmique. */
function rowChart(o) {
  return C.mount({ legend: o.legend }, function (W) {
    var rows = o.rows, rowH = o.rowH || 22, ml = o.ml || 104, mr = o.mr || 44, top = o.top || 20, bot = 24, H = top + rows.length * rowH + bot;
    var tx = function (v) { return o.log ? Math.log10(v) : v; }, a0 = tx(o.min), a1 = tx(o.max);
    var sx = function (v) { var c = Math.min(Math.max(v, o.min), o.max); return ml + (tx(c) - a0) / (a1 - a0) * (W - ml - mr); }, g = '';
    if (o.band) g += '<rect x="' + sx(o.band[0]) + '" y="' + (top - 6) + '" width="' + (sx(o.band[1]) - sx(o.band[0])) + '" height="' + (rows.length * rowH + 6) + '" fill="var(--violet-a)"/>';
    (o.ticks || []).forEach(function (t, i, all) { var x = sx(t[0]); g += '<line class="gl" x1="' + x + '" x2="' + x + '" y1="' + (top - 6) + '" y2="' + (top + rows.length * rowH) + '"/><text class="ax" x="' + x + '" y="' + (H - 8) + '" text-anchor="' + (i === all.length - 1 && x > W - mr - 16 ? 'end' : 'middle') + '">' + X(t[1]) + '</text>'; });
    (o.refs || []).forEach(function (r) { var x = sx(r.x); g += '<line x1="' + x + '" x2="' + x + '" y1="' + (top - 10) + '" y2="' + (top + rows.length * rowH) + '" stroke="var(--violet)" stroke-dasharray="4 3" stroke-width="1.2"/>' + (r.label ? '<text class="axl" x="' + (x + (r.end ? -4 : 4)) + '" y="' + (top - 10) + '" text-anchor="' + (r.end ? 'end' : 'start') + '" fill="var(--violet-2)">' + X(r.label) + '</text>' : ''); });
    rows.forEach(function (r, i) {
      var y = top + i * rowH + rowH / 2;
      g += '<text class="axl" x="' + (ml - 8) + '" y="' + (y + 3.5) + '" text-anchor="end"' + (r.strong ? ' fill="var(--hi)"' : '') + '>' + X(r.label) + '</text>';
      if (fin(r.a) && fin(r.b)) g += '<line x1="' + sx(r.a) + '" x2="' + sx(r.b) + '" y1="' + y + '" y2="' + y + '" stroke="var(--line-2)" stroke-width="2"/>';
      if (fin(r.a)) g += '<circle cx="' + sx(r.a) + '" cy="' + y + '" r="4" fill="var(--bg)" stroke="var(--soft)" stroke-width="1.5"/>';
      if (fin(r.b)) g += '<circle cx="' + sx(r.b) + '" cy="' + y + '" r="4.5" fill="var(--violet)"/>';
      if (r.right) g += '<text class="ax" x="' + (W - 2) + '" y="' + (y + 3.5) + '" text-anchor="end">' + X(r.right) + '</text>';
    });
    return { svg: '<svg viewBox="0 0 ' + W + ' ' + H + '" height="' + H + '">' + g + '</svg>' };
  });
}

function renderSetups(root) {
  var nCont = L.SETUPS.map(function (s) { return s.part; }), pMin = Math.min.apply(null, nCont), pMax = Math.max.apply(null, nCont);
  var fMin = Math.min.apply(null, L.SETUPS.map(function (s) { return s.facteur; })), fMax = Math.max.apply(null, L.SETUPS.map(function (s) { return s.facteur; }));
  root.appendChild(U.kpis([
    { label: 'Setups mesurés', value: String(L.SETUPS.length), hint: 'sur ' + L.NIVEAUX.length + ' niveaux calculés' },
    { label: 'Séances sans dérive', value: F.int(L.POOL.seances), hint: 'simulées à la barre' },
    { label: 'Contact brut', value: pc1(L.POOL.pBrut), hint: F.int(L.POOL.contacts) + ' fenêtres' },
    { label: 'Confirmé', value: pc1(L.POOL.pConf), tone: 'acc', hint: F.int(L.POOL.obs) + ' fenêtres' }
  ], 4));
  root.appendChild(U.callout([h('b', null, 'La confirmation ne déplace pas l’espérance, elle divise l’échantillon. '), 'Sur ' + F.int(L.POOL.obs) + ' contacts confirmés, le prix va dans le sens attendu ' + pc1(L.POOL.pConf) + ' du temps, contre ' + pc1(L.POOL.pBrut) + ' au contact brut : un demi, à ' + F.num(L.POOL.demi, 1) + ' point près. Elle retient de ' + pc1(pMax) + ' à ' + pc1(pMin) + ' des contacts, et multiplie d’autant le délai pour établir le setup : de ×' + F.num(fMin, 1) + ' à ×' + F.num(fMax, 1) + '.']));

  var s0 = U.section('Quatre termes, *et seulement quatre*', 'écrits avant le contact');
  s0.appendChild(U.flow({ nodes: [
    { ix: '1', title: 'Le niveau', sub: 'Un prix calculé sur le passé, jamais sur autre chose.', state: 'done' },
    { ix: '2', title: 'Le contact', sub: 'La minute où le prix vient le toucher.', state: 'done' },
    { ix: '3', title: 'La confirmation', sub: 'Ce qui doit se produire à ce contact, écrit d’avance.', state: 'done' },
    { ix: '4', title: 'L’invalidation', sub: 'Ce qui la dément ensuite, dans les 15 minutes.', state: 'active' }
  ] }));
  s0.appendChild(U.note('Un setup dont la confirmation se choisit après coup n’est pas un setup, c’est un commentaire.'));
  root.appendChild(s0);

  var s1 = U.section('Six niveaux, *calculés*', 'contacts par séance');
  s1.appendChild(C.bar({ cats: L.NIVEAUX.map(function (n) { return n.court; }), series: [{ name: 'Contacts par séance', values: L.NIVEAUX.map(function (n) { return n.contacts; }), tone: 'violet' }], horizontal: true, ml: 112, fmt: function (v) { return F.num(v, 2); } }));
  s1.appendChild(U.card({ title: 'Comment chaque niveau se calcule', meta: '4 familles', body: L.NIVEAUX.map(function (n) { return h('div', { class: 'mi-def' }, h('div', null, h('b', null, n.n), h('em', null, n.fam)), h('p', null, n.calc.charAt(0).toUpperCase() + n.calc.slice(1) + '. ' + F.num(n.contacts, 2) + ' contacts par séance.')); }) }));
  s1.appendChild(U.note('La deuxième bande VWAP est le niveau le plus touché : c’est ce qui en fait la seule famille dont le délai d’établissement se compte en années plutôt qu’en siècles. Elle est rare parce que deux écarts-types sont rares, ce qui est une propriété de la loi normale et non du marché.'));
  root.appendChild(s1);

  var s2 = U.section('Trois confirmations, *cinq seuils*', 'déclarés une fois pour toutes');
  L.CONFS.forEach(function (c) {
    s2.appendChild(U.card({ title: c.n, meta: c.crit.length + ' critères', body: [h('p', { class: 'mi-inv' }, c.idee), h('div', { class: 'mi-crit' }, c.crit.map(function (r) { return h('div', null, h('span', null, r[0]), h('b', null, r[1])); })), h('p', { class: 'mi-inv' }, h('b', null, 'Invalidation : '), c.inv + '.')] }));
  });
  s2.appendChild(U.note('Seuils déclarés dans alp1/setups.py : volume 1,5 × la médiane, z d’impact sous 0,25, mèche à 60 % de l’étendue, dépassement d’1 σ d’une minute, delta à 33 % du volume, fenêtre d’invalidation de 15 minutes. Le paragraphe de lecture de la table 6 écrit « deux fois le volume médian » ; ses lignes et le code disent 1,5, valeur retenue ici.'));
  root.appendChild(s2);

  var s3 = U.section('Ce que la confirmation *ne change pas*', 'P(sens attendu), table 7');
  var rows = L.SETUPS.map(function (s) { return { label: s.court, a: s.pBrut, b: s.pConf, right: pc1(s.pConf) }; });
  rows.push({ label: 'Les douze', a: L.POOL.pBrut, b: L.POOL.pConf, right: pc1(L.POOL.pConf), strong: true });
  s3.appendChild(rowChart({ rows: rows, min: 40, max: 56, ticks: [[40, '40 %'], [45, '45 %'], [50, '50 %'], [55, '55 %']], band: [50 - L.POOL.demi, 50 + L.POOL.demi], refs: [{ x: 50, label: 'pile ou face' }], legend: [{ label: 'contact brut', box: 'var(--bg)' }, { label: 'confirmé', box: 'var(--violet)' }] }));
  s3.appendChild(U.note('La bande violette est le demi-intervalle de la mise en commun (±1,4 point). Une cellule isolée s’en écarte parfois de 8,6 points : c’est le bruit d’un petit effectif, que la table publie exprès. Seule la dernière ligne tranche.'));
  s3.appendChild(U.table({ cols: [
    { k: 'n', label: 'Setup', cls: 'wrap' },
    { k: 'contacts', label: 'Contacts / séance', align: 'r', fmt: function (v) { return F.num(v, 2); } },
    { k: 'part', label: 'Part confirmée', align: 'r', fmt: pc1 }, { k: 'obs', label: 'Obs. indép.', align: 'r', fmt: F.int },
    { k: 'dementie', label: 'Part démentie', align: 'r', fmt: pc1 }, { k: 'pBrut', label: 'P brut', align: 'r', fmt: pc1 }, { k: 'pConf', label: 'P confirmé', align: 'r', fmt: pc1 },
    { k: 'mfe', label: 'MFE / MAE', align: 'r', fmt: function (v, r) { return r._pool ? 'rapport ' + F.num(L.POOL.rapport, 2) : F.num(v, 2) + ' / ' + F.num(r.mae, 2); } },
    { k: 'fam', label: 'Famille' }
  ], rows: L.SETUPS.concat([{ n: 'Les douze, mis en commun', fam: '—', obs: L.POOL.obs, pBrut: L.POOL.pBrut, pConf: L.POOL.pConf, _pool: true }]), rowClass: function (r) { return r._pool ? 'sel' : null; } }));
  root.appendChild(s3);

  var s4 = U.section('Ce qu’elle *coûte*', 'délai d’établissement, table 8');
  s4.appendChild(rowChart({ rows: L.SETUPS.map(function (s) { return { label: s.court, a: s.sans, b: s.avec, right: '×' + F.num(s.facteur, 1) }; }), min: 1, max: 2000, log: true, ticks: [[1, '1 an'], [10, '10'], [100, '100'], [1000, '1 000']], refs: [{ x: L.CARRIERE, label: 'carrière, 30 ans' }], legend: [{ label: 'sans confirmation', box: 'var(--bg)' }, { label: 'avec', box: 'var(--violet)' }] }));
  s4.appendChild(U.table({ cols: [
    { k: 'n', label: 'Setup', cls: 'wrap' }, { k: 'hz', label: 'Horizon' }, { k: 'N', label: 'Décisions requises', align: 'r', fmt: F.int },
    { k: 'cAn', label: 'Contacts / an', align: 'r', fmt: F.int }, { k: 'confAn', label: 'Confirmés / an', align: 'r', fmt: F.int },
    { k: 'sans', label: 'Délai sans', align: 'r', fmt: L.fmtAns }, { k: 'avec', label: 'Délai avec', align: 'r', fmt: L.fmtAns },
    { k: 'facteur', label: 'Facteur', align: 'r', fmt: function (v) { return '×' + F.num(v, 1); } },
    { k: 'muComp', label: 'µ compens. (pt/h)', align: 'r', fmt: function (v) { return F.num(v, 2); } },
    { k: 'muComp', label: 'Verdict (calculé)', fmt: function (v) { return L.verdictSetup(v); } }
  ], rows: L.SETUPS }));
  s4.appendChild(U.note('La dérive compensatrice est ce que la confirmation devrait apporter pour rembourser son délai : la dérive requise de l’horizon multipliée par la racine du facteur. Le verdict la compare au domaine plausible, 0,6 à 3,2 pt/h. Aucune valeur n’en sort, mais aucune n’est acquise : rien dans les 5 043 fenêtres mesurées ne dit qu’une confirmation déplace la dérive d’un centième de point.'));
  root.appendChild(s4);
  root.appendChild(U.note('Source : ALP nº 3, partie III, tables 6, 7 et 8 (900 séances sans dérive simulées à la barre, 12 sous-pas par minute). Aucun de ces nombres ne décrit ton marché : ils décrivent ce que vaut un setup quand il n’y a rien à lire, c’est-à-dire la loi nulle contre laquelle ton journal se juge.'));
}

/* ---------- 2.3 Seuil ---------- */
function loadSeuil() { return L.normSeuil(T.store.get(K.seuil, null)); }
function saveSeuil(s) { T.store.set(K.seuil, s); }

function renderSeuil(root, ctx) {
  var st = loadSeuil(), set = ctx.settings;
  var sP = U.section('Instrument', 'préréglages modifiables');
  var presetBox = h('div', { style: 'display:flex;flex-direction:column;gap:8px' });
  function paintPreset() {
    T.clear(presetBox); var s = loadSeuil(), P = L.PRESETS[s.preset], fc = L.frictionOf(set);
    presetBox.appendChild(U.chips({ options: L.PRESET_IDS.map(function (k) { return { v: k, label: L.PRESETS[k].n }; }), value: s.preset, onChange: function (k) { saveSeuil(L.applyPreset(loadSeuil(), k, set)); T.toast('Instrument : ' + L.PRESETS[k].n); ctx.rerender(); } }));
    var lab = s.preset === 'moi' ? 'Ta friction, tirée des réglages : commission ' + F.usd(set.commissionRT, 2) + ' aller-retour ÷ ' + F.num(set.pointValue, 0) + ' $ le point, plus un tick de sortie (' + F.num(set.tick, 2) + ' pt) : c = ' + F.num(fc, 2) + ' pt.' : P ? P.lab : 'Paramètres libres, saisis à la main.';
    presetBox.appendChild(U.note(lab + (s.preset !== 'ref' && s.s1 === 1.25 && s.sS === 60 ? ' Les σ sont encore ceux de la référence ES : remplace-les par tes mesures.' : ''), s.preset !== 'ref' && s.s1 === 1.25 && s.sS === 60));
    typo(presetBox);
  }
  paintPreset(); sP.appendChild(presetBox); root.appendChild(sP);

  var sG = U.section('Géométrie', 'stop = σ√h à 1:2, ou stop en % à 1:20');
  var hs = [5, 15, 30, 45, 60];
  sG.appendChild(U.chips({ options: hs.map(function (m) { return { v: m, label: 'lecture ' + m + ' min' }; }), value: hs.filter(function (m) { return Math.abs(st.a - st.s1 * Math.sqrt(m)) < 1e-9 && st.rr === 2; })[0], onChange: function (m) { saveSeuil(L.applyHorizon(loadSeuil(), m)); T.toast('Lecture à ' + m + ' min · 1:2'); ctx.rerender(); } }));
  if (st.preset === 'ref') {
    var geos = [[0.010, 'déclarée 0,010 %'], [0.050, '0,050 %'], [0.150, 'élargie 0,150 %']];
    sG.appendChild(U.chips({ options: geos.map(function (g) { return { v: g[0], label: g[1] + ' · 1:20' }; }), value: geos.map(function (g) { return g[0]; }).filter(function (g) { return Math.abs(st.a - st.level * g / 100) < 1e-9 && st.rr === 20; })[0], onChange: function (g) { saveSeuil(L.applyGeo(loadSeuil(), g)); T.toast('Stop ' + F.num(g, 3) + ' % · 1:20'); ctx.rerender(); } }));
  }
  root.appendChild(sG);

  var sF = U.section('Paramètres', 'virgule acceptée');
  function fld(k, label, unit, min) {
    return { id: 'mi-' + k, label: label, unit: unit, value: Math.round(st[k] * 1e4) / 1e4, min: min, onChange: function (v) {
      var s = loadSeuil(); s[k] = v; if (['level', 's1', 'sS', 'c', 'T'].indexOf(k) >= 0) s.preset = 'libre'; saveSeuil(s); paintPreset(); request();
    } };
  }
  sF.appendChild(U.fields([fld('a', 'Stop', 'pt', 0.01), fld('rr', 'R:R (1:x)', '', 0.05), fld('c', 'Friction c aller-retour', 'pt', 0), fld('drift', 'Dérive déclarée', 'pt/h'), fld('s1', 'σ 1 minute', 'pt', 0.01), fld('sS', 'σ séance', 'pt', 0.01), fld('T', 'Séance', 'min', 2), fld('level', 'Niveau de référence', 'pt', 1)]));
  sF.appendChild(U.note('La dérive déclarée est une hypothèse que tu poses à part, jamais tirée de la friction : c’est la circularité qu’ALP nº 1 a payée.'));
  root.appendChild(sF);

  var sR = U.section('Résultat', 'calcul exact, en tâche de fond');
  var box = h('div', { style: 'display:flex;flex-direction:column;gap:12px' });
  sR.appendChild(box); root.appendChild(sR);
  root.appendChild(U.note('Source : port exact du calculateur de plan de séance, lui-même vérifié contre les modules d’ALP (horizon, seuil, speculation, entropy). Référence ES à 1:20 : stop 0,6 pt (0,010 %) → µ* 8,189 pt/h et 474 décisions ; 3 pt (0,050 %) → 10 568 décisions ; 9 pt (0,150 %) → µ* 0,196 pt/h (ALP nº 3, parties XI, XIII et XXX).'));

  function request() {
    var p = L.calcParams(loadSeuil()), key = JSON.stringify(p);
    if (UI.cache[key]) { paint(UI.cache[key], loadSeuil()); return; }
    T.clear(box); box.appendChild(U.empty({ title: 'Calcul…', text: 'Séries de Fourier sur la séance entière : une fraction de seconde.' }));
    var id = ++UI.req;
    T.compute(L.seuil, p).then(function (r) { UI.cache[key] = r; if (id === UI.req && box.isConnected) paint(r, loadSeuil()); }, function (e) { if (id === UI.req && box.isConnected) paint({ err: String(e && e.message || e) }, loadSeuil()); });
  }
  function paint(c, s) {
    T.clear(box);
    var v = L.verdict(c);
    if (c.err) { box.appendChild(U.empty({ title: 'Calcul impossible', text: c.err })); return; }
    var cond = h('div', null,
      h('div', { class: 'mi-cond' }, h('div', null, h('b', null, 'Dérive : µ* ≤ 3,2 pt/h'), h('span', null, 'µ* = ' + L.fmtMu(c.mu) + ' pt/h')), U.pill(c.payante ? 'passe' : 'échoue', c.payante ? 'acc' : 'no')),
      h('div', { class: 'mi-cond' }, h('div', null, h('b', null, 'Portée : objectif ≤ 1 σ de séance'), h('span', null, 'objectif ' + F.num(c.b, 2) + ' pt pour ' + F.num(c.ecartSeance, 1) + ' pt de séance')), U.pill(c.aPortee ? 'passe' : 'échoue', c.aPortee ? 'acc' : 'no')));
    box.appendChild(U.card({ title: 'Verdict', meta: U.pill(v.pill, v.tone), accent: c.ok, body: [
      h('p', { class: 'mi-vt' }, v.text), cond,
      h('div', null, C.gauge({ value: c.mu, min: 0.1, max: 30, log: true, band: L.PLAUS, ticks: [[0.1, '0,1'], [0.6, '0,6'], [3.2, '3,2'], [30, '30']] }), h('span', { class: 'mi-src' }, 'µ* sur l’échelle logarithmique ; la bande est le domaine plausible, 0,6 à 3,2 pt/h.'))
    ] }));
    var yrs = c.N / (2 * L.SESSIONS_PER_YEAR);
    box.appendChild(U.kpis([
      { label: 'Seuil borné · Wald', value: L.fmtMu(c.mu), unit: 'pt/h', tone: c.payante ? 'acc' : 'neg', hint: 'µ* = c / E[τ∧T]' },
      { label: 'Seuil non borné', value: L.fmtMu(c.muNB), unit: 'pt/h', hint: 'deux barrières seules' },
      { label: 'Portée', value: F.num(c.portee, 2), unit: 'σ séance', tone: c.aPortee ? null : 'neg', hint: 'objectif / σ√T' },
      { label: 'R:R max', value: '1:' + F.num(c.rrMax, 1), hint: 'P(objectif) ≥ 5 %' },
      { label: 'Taux requis', value: F.pct(c.eqRate, 2), hint: 'taux nul ' + F.pct(c.nullRate, 2) },
      { label: 'Décisions requises', value: F.int(c.N), hint: fin(yrs) ? F.num(yrs, 1) + ' an à 2 par séance' : '—' },
      { label: 'E[R] à dérive 0', value: F.num(c.er0, 3, 'R', true), tone: 'neg', hint: 'la friction seule, −c/a' },
      { label: 'E[R] à ' + F.num(s.drift, 1) + ' pt/h', value: F.num(c.erD, 3, 'R', true), tone: c.erD > 0 ? 'acc' : 'neg', hint: 'dérive déclarée' },
      { label: 'Temps exposé', value: F.num(c.expo, 2), unit: 'min', hint: 'E[τ∧T]' },
      { label: 'Case', value: F.num(c.caseMin, 1), unit: 'min', hint: 'tenue minimale, c / 3,2' }
    ], 3));
    box.appendChild(U.card({ title: 'Trois fins', meta: 'à dérive nulle', body: [
      h('div', { class: 'mi-bar', role: 'img', 'aria-label': 'Objectif ' + F.pct(c.pObj, 1) + ', stop ' + F.pct(c.pStop, 1) + ', cloche ' + F.pct(c.pOpen, 1) }, h('i', { class: 'o', style: 'width:' + (c.pObj * 100) + '%' }), h('i', { class: 's', style: 'width:' + (c.pStop * 100) + '%' }), h('i', { class: 'c', style: 'width:' + (c.pOpen * 100) + '%' })),
      h('div', { class: 'mi-lg' }, h('span', null, h('i', { class: 'o' }), 'objectif ' + F.pct(c.pObj, 1)), h('span', null, h('i', { class: 's' }), 'stop ' + F.pct(c.pStop, 1)), h('span', null, h('i', { class: 'c' }), 'cloche ' + F.pct(c.pOpen, 1))),
      h('p', { class: 'mi-inv' }, 'Stop ' + F.num(c.a, 2) + ' pt, objectif ' + F.num(c.b, 2) + ' pt. Une position a trois fins, pas deux : la sortie au marché parce que la séance se ferme ne se déclare pas. À dérive nulle, achat et vente rendent le même nombre ; tout écart entre les deux sens est la dérive, rien d’autre.')
    ] }));
    var hz = [];
    if (fin(c.hOpt)) hz.push({ v: c.hOpt, label: 'épreuve · ' + F.num(c.hOpt, 0) + ' min' });
    if (c.hMin != null && fin(c.hMin)) hz.push({ v: c.hMin, label: 'plus courte · ' + F.num(c.hMin, 1) + ' min' });
    box.appendChild(U.card({ title: 'Deux horizons calculés', meta: 'à 1:2', body: [
      U.chips({ options: hz, value: hz.map(function (o) { return o.v; }).filter(function (m) { return Math.abs(s.a - s.s1 * Math.sqrt(m)) < 1e-9 && s.rr === 2; })[0], onChange: function (m) { saveSeuil(L.applyHorizon(loadSeuil(), m)); T.toast('Lecture à ' + F.num(m, 1) + ' min · 1:2'); ctx.rerender(); } }),
      h('p', { class: 'mi-inv' }, (fin(c.hOpt) ? 'L’épreuve, ' + F.num(c.hOpt, 0) + ' min, est l’horizon où une dérive de 3,2 pt/h, si elle existait, se verrait le plus vite : écart directionnel de ' + F.num(c.ecartOpt, 1) + ' points de taux. ' : '') + (c.hMin != null ? 'La lecture la plus courte qui passe les deux conditions à 1:2 dure ' + F.num(c.hMin, 1) + ' min, stop ' + F.num(c.aMin, 2) + ' pt ; en deçà, l’exposition tombe sous la case et µ* sort du domaine.' : 'Aucune lecture à 1:2 ne passe les deux conditions avec ces paramètres.'))
    ] }));
    box.appendChild(U.note('µ* borné : c / E[τ∧T], temps d’exposition sous loi d’échelle (H = ' + F.num(c.H, 3) + '), la route du document. µ* non borné : le problème à deux barrières sans fin de séance, qui ne retourne pas le verdict mais en change l’ampleur. Les décisions requises supposent un test unilatéral à 95 % et une puissance de 80 %.'));
    typo(box);
  }
  request();
}

/* ---------- 2.4 Lectures ---------- */
function scatterLectures(rows) {
  var byH = []; rows.forEach(function (r) { var g = byH.find(function (x) { return x.m === r.minutes; }); if (!g) byH.push(g = { m: r.minutes, hz: r.hz, rows: [] }); g.rows.push(r); });
  return C.mount({ legend: [{ label: 'établissable en 30 ans', box: 'var(--violet)' }, { label: 'au-delà', box: 'var(--bg)' }, { label: 'lieu d’une carrière', tone: 'mute', dash: true }] }, function (W) {
    var H = 248, m = { l: 50, r: 16, t: 14, b: 40 }, x0 = Math.log10(3.5), x1 = Math.log10(1170), y0 = Math.log10(5), y1 = Math.log10(40000);
    var sx = function (v) { return m.l + (Math.log10(v) - x0) / (x1 - x0) * (W - m.l - m.r); }, sy = function (v) { return m.t + (1 - (Math.log10(v) - y0) / (y1 - y0)) * (H - m.t - m.b); }, g = '';
    [10, 100, 1000, 10000].forEach(function (v) { g += '<line class="gl" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + sy(v) + '" y2="' + sy(v) + '"/><text class="ax" x="' + (m.l - 7) + '" y="' + (sy(v) + 3.5) + '" text-anchor="end">' + X(F.int(v)) + '</text>'; });
    [[5, '5 min', 0], [15, '15 min', 0], [60, '1 h', 0], [120, '2 h', 0], [390, '1 séance', 0], [1170, '3 séances', 1]].forEach(function (t, i, all) { var x = sx(t[0]); g += '<line class="gl" x1="' + x + '" x2="' + x + '" y1="' + (H - m.b) + '" y2="' + (H - m.b + 4 + t[2] * 12) + '"/><text class="ax" x="' + x + '" y="' + (H - m.b + 15 + t[2] * 12) + '" text-anchor="' + (i === all.length - 1 ? 'end' : 'middle') + '">' + X(t[1]) + '</text>'; });
    g += '<path d="M' + byH.map(function (b) { return sx(b.m).toFixed(1) + ',' + sy(b.rows[0].N / L.CARRIERE).toFixed(1); }).join(' L') + '" fill="none" stroke="var(--soft)" stroke-dasharray="5 4" stroke-width="1.2"/>';
    g += '<text class="axl" x="' + (m.l + 4) + '" y="' + (m.t + 10) + '">décisions offertes par an</text>';
    rows.forEach(function (r) { var ok = L.annees(r.delai) < L.CARRIERE; g += '<circle cx="' + sx(r.minutes) + '" cy="' + sy(r.an) + '" r="' + (ok ? 4.5 : 4) + '" fill="' + (ok ? 'var(--violet)' : 'var(--bg)') + '" stroke="' + (ok ? 'var(--violet)' : 'var(--soft)') + '" stroke-width="1.5"/>'; });
    g += '<line class="hl" x1="0" x2="0" y1="' + m.t + '" y2="' + (H - m.b) + '" stroke="var(--violet)" style="opacity:0"/>';
    return { svg: '<svg viewBox="0 0 ' + W + ' ' + H + '" height="' + H + '">' + g + '</svg>', hover: { xs: byH.map(function (b) { return sx(b.m); }), html: function (i) { var b = byH[i]; return '<b>' + X(b.hz) + '</b> · ' + X(F.int(b.rows[0].N)) + ' décisions requises<br>' + b.rows.map(function (r) { return X(r.nom) + ' : ' + X(F.int(r.an)) + ' / an · ' + X(L.fmtDelai(r.delai)); }).join('<br>'); } } };
  });
}

function renderLectures(root, ctx) {
  var rows = L.ordre(), nOk = L.etablissables(), prods = L.LECTURES.map(function (x) { return x.muN; });
  var sel = UI.lect != null ? UI.lect : T.store.get(K.lect, 1), cur = rows.find(function (r) { return r.n === sel; }) || rows[0];
  root.appendChild(U.kpis([
    { label: 'Lectures', value: String(rows.length), hint: L.familles().length + ' familles' },
    { label: 'Établissables', value: nOk + ' / ' + rows.length, tone: 'acc', hint: 'en moins de ' + L.CARRIERE + ' ans' },
    { label: 'Taux nul', value: F.num(L.TAUX_NUL, 2, '%'), hint: 'à 1:2, sans friction' },
    { label: 'Seuil × décisions', value: F.int(Math.min.apply(null, prods)) + '–' + F.int(Math.max.apply(null, prods)), hint: 'quinze lectures' }
  ], 4));

  var s1 = U.section('Ce que chaque lecture *offre*', 'horizon et décisions par an, échelles log');
  s1.appendChild(scatterLectures(rows));
  s1.appendChild(U.note('Chaque point est une lecture : son horizon, et le nombre de décisions qu’elle offre par an (occasions × fréquence du motif × 252 séances). La courbe en tirets est le lieu des lectures qu’une carrière de 30 ans suffit tout juste à établir ; au-dessus, la lecture se tranche, en dessous elle reste une opinion.'));
  root.appendChild(s1);

  var s2 = U.section('Le catalogue, *dans l’ordre*', 'touche une ligne pour sa fiche');
  s2.appendChild(U.table({ cols: [
    { k: 'rang', label: '#', align: 'r' }, { k: 'nom', label: 'Lecture', cls: 'wrap' }, { k: 'hz', label: 'Horizon' },
    { k: 'occ', label: 'Occasions / séance', align: 'r', fmt: function (v) { return F.num(v, 2); } },
    { k: 'freq', label: 'Fréq. sans dérive', align: 'r', fmt: pc1 },
    { k: 'mu', label: 'µ* (pt/h)', align: 'r', fmt: function (v) { return F.num(v, 3); } },
    { k: 'N', label: 'Décisions', align: 'r', fmt: F.int }, { k: 'an', label: 'Par an', align: 'r', fmt: F.int },
    { k: 'delai', label: 'Délai', align: 'r', fmt: function (v) { return L.fmtDelai(v); } }
  ], rows: rows, rowClass: function (r) { return r.n === cur.n ? 'sel' : null; }, onRow: function (r) { UI.lect = r.n; T.store.set(K.lect, r.n); ctx.rerender(); requestAnimationFrame(function () { var el = document.getElementById('mi-fiche'); if (el && el.scrollIntoView) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }); } }));
  s2.appendChild(U.note('L’ordre n’est pas écrit : il est celui de l’horizon, converti en minutes (une séance vaut 390 min), du plus court au plus long. Il va donc de la lecture qu’on peut prouver à celle qu’on ne pourra pas.'));
  root.appendChild(s2);

  var ok = L.annees(cur.delai) < L.CARRIERE;
  var s3 = U.section('Fiche · *' + cur.nom.toLowerCase() + '*', cur.fam + ' · ' + cur.hz);
  var fiche = U.card({ title: '#' + cur.rang + ' · ' + cur.nom, meta: U.pill(ok ? 'établissable' : 'hors carrière', ok ? 'acc' : 'no'), accent: ok, body: [
    h('div', { class: 'mi-fi' },
      h('p', null, h('b', null, 'La situation : '), cur.sit + '.'),
      h('p', null, h('b', null, 'Ce qu’on en attend : '), cur.att + '.'),
      h('p', null, h('b', null, 'Sa loi nulle : '), cur.loi + '.')),
    U.kpis([
      { label: 'Fréquence nulle', value: pc1(cur.freq), hint: 'sans rien à lire' },
      { label: 'Occasions', value: F.num(cur.occ, 2), hint: 'par séance' },
      { label: 'Déplacement médian', value: F.num(0, 2), unit: 'pt', hint: 'sans dérive' },
      { label: 'À 3,2 pt/h', value: F.num(cur.depH, 2), unit: 'pt', hint: '+' + F.num(cur.gain, 1) + ' points de proba' },
      { label: 'Dérive requise', value: F.num(cur.mu, 3), unit: 'pt/h', hint: 'µ*, taux requis ' + F.num(cur.req, 2, '%') },
      { label: 'Délai', value: L.fmtDelai(cur.delai), tone: ok ? 'acc' : 'neg', hint: F.int(cur.N) + ' décisions' }
    ]),
    h('p', { class: 'mi-inv' }, 'Géométrie de lecture : stop à l’écart-type de l’horizon (' + F.num(cur.a, 2) + ' pt), cible à deux fois le stop, friction de référence 0,33 pt. Le déplacement médian sans dérive vaut zéro pour les quinze lectures : reconnaître le motif, à lui seul, n’apprend rien sur la suite.')
  ] });
  fiche.id = 'mi-fiche';
  s3.appendChild(fiche);
  root.appendChild(s3);

  root.appendChild(U.callout([h('b', null, 'Aucun horizon avantageux. '), 'La dérive requise s’effondre avec l’horizon (' + F.num(L.LECTURES[0].mu, 3) + ' pt/h à 5 min, ' + F.num(L.LECTURES[14].mu, 3) + ' à 3 séances) quand le nombre de décisions explose (' + F.int(L.LECTURES[0].N) + ' contre ' + F.int(L.LECTURES[14].N) + '). Leur produit ne bouge pas : choisir un horizon n’est pas un choix de qualité, c’est un choix de monnaie — payer en exigence sur le marché, ou en patience.']));
  root.appendChild(U.note('Source : ALP nº 3, partie III, tables 2, 3 et 5. Fréquences mesurées sous prix sans dérive (lois du dépôt ou détecteur sur 400 séances). Déplacements en points d’indice de la référence ES ; « à 3,2 pt/h » est la dérive la plus forte du domaine plausible.'));
}

/* ---------- 2.5 Montage ---------- */
var HEAD = {
  plan: { k: 'Stratégie · Plan', t: 'Trois filtres, *un* trade.', l: 'Ton plan de nuit sur la VWAP : la tendance et le GEX donnent le biais, la VWAP filtre, un seul déclencheur décide. Chaque refus s’inscrit au journal, sans sens ni mise.' },
  setups: { k: 'Stratégie · Setups', t: 'Un motif n’est pas *un setup*.', l: 'Un niveau calculé, un contact, une confirmation écrite d’avance, une invalidation. Douze setups mesurés sur 900 séances sans dérive (ALP nº 3, partie III).' },
  seuil: { k: 'Stratégie · Seuil', t: 'La géométrie, *avant* le signal.', l: 'µ* = c / E[τ∧T] : la dérive qu’il faudrait pour que ta géométrie paie sa friction. Le stop la fixe entièrement ; le marché n’y est pour rien.' },
  lectures: { k: 'Stratégie · Lectures', t: 'Quinze lectures, *dans l’ordre*.', l: 'Le catalogue d’ALP nº 3, rangé par horizon : la fréquence de chaque motif quand il n’y a rien à lire, et le temps qu’il faudrait pour l’établir.' }
};
var RENDER = { plan: renderPlan, setups: renderSetups, seuil: renderSeuil, lectures: renderLectures };
T.desk({
  id: 'micro', label: 'Stratégie intraday', glyph: 'µ', group: 'Marché', order: 30,
  tabs: [{ id: 'plan', label: 'Plan' }, { id: 'setups', label: 'Setups' }, { id: 'seuil', label: 'Seuil µ*' }, { id: 'lectures', label: 'Lectures' }],
  render: function (root, ctx) {
    injectCss();
    var tab = HEAD[ctx.tab] ? ctx.tab : 'plan', hd = HEAD[tab];
    root.appendChild(U.page({ kicker: hd.k, title: hd.t, lede: hd.l }));
    root.appendChild(U.tabs({ tabs: this.tabs, value: tab, onChange: ctx.setTab }));
    var cleanup = RENDER[tab](root, ctx);
    typo(root);
    return cleanup;
  }
});
