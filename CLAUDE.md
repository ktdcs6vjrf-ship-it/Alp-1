# ALP-1 — mémoire de projet

Ce fichier existe pour qu'une session repartie de zéro retrouve l'état du
travail sans le redécouvrir. Le dépôt est la seule mémoire : ce qui n'est pas
écrit ici ou commité n'existe plus.

**Si vous venez d'un `/clear` : lisez ce fichier en entier avant de toucher
quoi que ce soit.** Il contient les pièges déjà tombés dedans, et ils sont
tous du genre à ne pas se voir.

## Ce qu'est ce dépôt

Deux papiers de recherche en français, de forme SSRN, sur l'intraday indice.
Le noyau est un ensemble de modules Python qui **calculent** les chiffres, et
les documents HTML sont **construits** à partir d'eux. Aucun nombre n'est
écrit à la main dans un document.

**ALP nº 1** — `docs/temps-de-marche-et-peremption.html` (≈1,06 Mo, 50 sections
en neuf parties, 109 tables, 50 figures). L'invariance des géométries de
sortie. Chaîne : `report*.py` + `fig*.py` → `workingpaper.py`. Sa section 18
(`report15.py` + `fighyp.py`) audite sa propre hypothèse d'edge : voir
« la circularité » plus bas.

**ALP nº 3** — `docs/prouver-un-jugement.html` (175 sections en trente
et une parties, 182 tables, 275 figures dont soixante-dix-huit surfaces en
nuage de points). L'évaluation d'un opérateur discrétionnaire dont l'avantage n'est pas
codable, puis **le catalogue des quinze lectures**, puis **la grammaire du
setup**, puis le seuil de rentabilité, puis les concepts de sortie, puis la
lecture du flux. Chaîne : `journal.py` → `operator.py` → `attribution.py` →
`report10/11/13/14.py` + `sorties.py` + `concepts.py` + `setups.py` +
`figdisc.py` + `figflux.py` + `figsortie.py` + `figcat.py` + `figsetup.py` +
`robustesse.py` + `figrobu.py` + `overnight.py` + `figon.py` +
`emprunts.py` + `figemp.py` + `fonds.py` + `figfds.py` + `revue.py` +
`figrev.py` + `niveaux.py` + `fignv.py` + `grandeurs.py` + `figgra.py` +
`theta.py` + `figth.py` + `vega.py` + `figvg.py` + `rho.py` + `figrh.py` + `vanna.py` +
`figva.py` + `charm.py` + `figch.py` + `volga.py` + `figvo.py` +
`ordres.py` + `figord.py` + `implicite.py` + `figiv.py` +
`skew.py` + `figsk.py` + `speculation.py` + `figspec.py` → `discpaper.py`. Titre courant : *Le seuil, et non le signal*.

Sa **partie III** est le catalogue : quinze lectures — footprint, carnet, CVD,
VWAP, Fibonacci, profil de volume, profil de marché, gamma, structure de Dow —
rangées par horizon **calculé**, chacune avec sa fréquence sous prix sans
dérive, un exemple tiré d'une séance sans dérive, la réaction du prix ensuite,
et le délai qu'il faudrait pour l'établir. Elle répond à la question d'ordre
que posait le document : le footprint y vient en premier, non par importance
mais parce qu'il est la seule famille prouvable à l'échelle d'une carrière.
Les lois nulles détaillées du flux restent en partie XIII.

Ses quatre dernières sections (14 à 17) sont **la grammaire du setup** —
`setups.py` + `figsetup.py`. Un motif n'est pas un setup : un setup est un
niveau **calculé**, un contact, une confirmation écrite d'avance, une
invalidation. Six niveaux × trois confirmations = douze setups, mesurés sur
900 séances sans dérive simulées **à la barre** (12 sous-pas, volume, coupe
bid/ask, footprint rejouable). Résultat : *la confirmation ne déplace pas
l'espérance, elle divise l'échantillon* — 49,4 % contre 50,1 % dans le sens
attendu, pour 89 à 98 % d'occasions en moins et un délai multiplié d'autant.
Le coût se convertit en dérive compensatrice (0,24 à 1,60 pt/h), et le verdict
qui la compare au domaine plausible est **calculé, jamais écrit**.

Deux autres builds existent — `docs/alp1-paper.html` (`--paper`), version
plus ancienne et plus courte d'ALP nº 1, et `docs/alp2-paper.html`
(`--paper2`), la bande de bruit. Il partage `report*.py` : **une correction
de module s'y propage, donc il faut le rebâtir aussi — et le balayer.** Il a
vécu longtemps hors des trois balayages, et y gardait six chevauchements que
les deux autres documents n'avaient pas.
Dernier artefact : https://claude.ai/code/artifact/c452a408-3263-431f-8b53-373553f12c9b

Derniers artefacts publiés :
- ALP nº 3 : https://claude.ai/code/artifact/23f16e50-d604-461d-bc24-533226520666
  (précédents : b9a9ac4d, 1d4e0835, 0bf1fb72, 9d9ad6dc, 96060108, 9131a050, 6aa40bf9, 340834bd, 5a666d3a, 9e0ef040,
  8edc727c, b40a2d6b, e5f06e51, 614afa35, 213dccda, a990ef0e, c2cbc5ee,
  d1e5eca9, 82bd1a42, 601106cf, dcb59260, d5e2c22b, 99a53614, f9f5d005,
  4e95dfbc, e49bcb16, c360de80)
- ALP nº 1 : https://claude.ai/code/artifact/d6e866f5-1875-4cda-b639-11da99cae35c

L'utilisateur veut **un nouveau lien à chaque amélioration** — publier sous un
nouveau chemin de fichier, jamais republier le même.

## Règles du dépôt — à ne pas enfreindre

1. **Stdlib uniquement.** Pas de numpy, pas de scipy, pas de pandas.
   Python 3.11+. Tout aléa est déterministe et amorcé par une graine explicite.
   (C'est pourquoi `spectrum.py` porte son propre Jacobi.)
2. **Les figures n'écrivent aucune couleur en dur.** Elles passent par les
   jetons CSS de `alp1/figcss.py`. `tests/test_figures_all.py` balaie les
   modules `fig*.py` et refuse tout `#rrggbb` — y compris les entités HTML de
   la forme `&#8202;`, qui doivent être écrites en caractère littéral. Ajouter
   un module de figures sans l'inscrire dans `MODULES` fait échouer le premier
   test, ce qui est voulu.
3. **Les comptes annoncés sont gardés par les tests.** `tests/test_docs.py`
   vérifie que le README dit vrai, `tests/test_workingpaper.py` et
   `tests/test_discpaper.py` vérifient la structure des documents (sections,
   parties, tables, figures, rangs des renvois). Changer l'un impose de
   changer l'autre.
4. **Le document se reconstruit, il ne s'édite pas.** On modifie
   `docs/*.template.html`, puis `python main.py --wp` / `--discpaper`.
5. **Toute méthode nouvelle vient avec sa loi nulle.** C'est la méthodologie
   centrale : un motif ne vaut que comparé à sa fréquence sous un prix sans
   dérive. Un estimateur qu'on ne sait pas calibrer contre son bruit ne rentre
   pas.
6. **Un paramètre déclaré n'est jamais dérivé de ce qu'il sert à évaluer.**
   Corollaire du piège de circularité ci-dessous.

## Les deux résultats structurants

**L'arrêt optionnel.** Par l'identité de Wald à temps borné par la séance,
`E[R] = (µ·E[τ∧T] − c)/L`, d'où un seuil `µ* = c/E[τ∧T]`. À `µ = 0`,
`E[R] = −c/L` pour toute géométrie : aucune géométrie ne crée d'espérance,
elle achète du temps de marché. `µ` est une propriété du marché ; **`µ*` est
une propriété de la géométrie, et l'opérateur la fixe entièrement.**

Conséquences chiffrées, toutes dans ALP nº 3 partie X :
- stop déclaré 0,010 % → µ* = 8,19 pt/h, hors du domaine plausible (0,6–3,2) ;
- stop 0,150 % → µ* = 0,196, un facteur 53 sur ce seul levier, quand améliorer
  l'exécution n'en donne que 3,5 ;
- espérance de −0,416 R à +0,337 R **à dérive identique**.

**Le budget d'information.** À la géométrie déclarée, une décision doit porter
0,941 % d'un bit : le marché peut être du bruit à 99,06 %. Au stop élargi,
0,042 % — bruit à 99,958 %. Le prix : 474 décisions pour établir la première,
10 568 pour la seconde. **Rendre l'exigence petite la rend indémontrable.**

## Hors du corpus — le mandat NQ

`docs/mandat/` porte un objet qui n'appartient pas à la chaîne des papiers :
un **fichier HTML autonome** — un `<style>` en ligne, un `<script>` en ligne,
aucune dépendance, aucune construction — publié en artefact et envoyé à un
bailleur privé. Treize planches SVG écrites à la main, noir et blanc strict,
aléa déterministe (mulberry32 + MA(1) à coefficient négatif pour le rebond
bid-ask). Il ne passe par aucun module Python et par aucun test du dépôt ;
son `README.md` liste ses règles, ses pièges et ses scripts de vérification.

Deux règles y engagent l'auteur. **Un nouveau lien à chaque édition** : on
copie le fichier sous un nouveau nom, on ne republie jamais la même URL.
**Aucun défilement horizontal à aucune largeur** — vérifié à 360, 390, 430,
768 et 1100 px ; sous 760 px le drapeau `ETROIT` fait passer les planches
d'une boîte de 1000 à une boîte de 430, faute de quoi un intitulé de 14 px
se rend à 5,5 px.

Le piège qui résume les autres : **la relecture visuelle se faisait dans une
police de repli**, plus large que celle qui est livrée. Les vraies fontes se
récupèrent par npm et s'injectent dans un aperçu local — c'est ce qui a rendu
visibles la moitié des défauts de rendu du document.

## Hors du corpus — ALP Desk

`desk/` porte le terminal mobile de préparation MNQ de l'utilisateur : quatorze desks
(hub, plan de trading, macro, NQ, stratégie intraday, risque, R&D, labo, quant,
métriques, journal, routine, données, réglages) assemblés par `desk/build.py` en **une seule page HTML**, publiée en
artefact avec `db` + `user`. JavaScript sans dépendance, tests en node
(`desk/test/*.test.js`, 8 685 contrôles) et banc de rendu Playwright à 390 et
1280 px. Il ne participe à aucun test Python ; il cite ALP nº 3 avec sa source et
recoupe ses nombres contre `desk/ref/alp3txt/`. **Aucun chiffre de marché n'y est
écrit** : les rapports macro et le calendrier sont des documents que Claude écrit
dans les collections `macro` et `calendar` de l'artefact (schémas dans
`desk/CONTRACT.md`) à partir des captures que l'utilisateur envoie, traduites en
français. Un nouveau lien à chaque amélioration, comme pour le reste. Dernier
artefact : https://claude.ai/artifact/LMuRjnu65akSE8LeEggTvN (précédents RUirhupXYNSPHSMGp9BTDH, 1772yYTUpYmuAkEJ7DQWm2, DgoivKfGJjD8mrJ4UFzGwD). Lire
`desk/README.md` avant d'y toucher.

## Hors du corpus — Alp-0 Zones (Pine)

`pine/alp0-zones.pine` : l'indicateur TradingView de l'utilisateur pour NQ /
MNQ — VWAP σ réglé comme « The Strategists », relevés Gexbot collés par son
assistant Lou au format **ALPZ 1**, confluences, touches et issues sur bougie
confirmée, profil GEX 0DTE à droite. **Étape 1** de son cahier des charges
(plus le profil de l'étape 2) ; restent la comparaison minuit / 5 h et
l'étape 3 (structures, confirmations, statistiques). Le format, l'exemple
fictif et les règles sont dans `docs/zones-gamma-format.md` ; le banc
`tools/zones-pinets/` exécute le vrai fichier sous PineTS (131 contrôles) —
ce n'est pas le compilateur TradingView. Le z-score de l'utilisateur
(« Z + Single Prints (OPEX) ») y est intégré en tête, corrigé. Version
affichée en tête du tableau (`VERSION`), à incrémenter à chaque livraison :
c'est elle qui dit à l'utilisateur quel code tourne sur son graphique. Un **mode
démo** (groupe ⑤) pose des niveaux inventés, marqués DÉMO, pour tester
l'affichage sans donnée. Page :
https://claude.ai/artifact/HxTeeNfPKF52SyL24oyzMN (v4, mode démo ; précédentes
7Nvvsf92N1ZESrvg48PFG5, 2kE8QktJ7nGt8GfjENGA6f, HPJD3LA8YSHLMpdZusxYWF). Consigne du bot de relevés (« Lou », que
l'utilisateur appelle aussi « grok bot ») : `docs/consigne-lou-alpz.md`, page
https://claude.ai/artifact/F18pWMEua798hG23GEM4Q5 ; son exemple est exécuté
par le banc (scénario P). Session du 7 novembre 2026
sur la branche `claude/exciting-dijkstra-ks25vr`, imposée par la session.

**Décision de l'utilisateur, 7 novembre 2026 : « on laisse tomber » les zones
Gexbot.** Il ne garde que la heatmap z-score et le VWAP, dans un seul script
autonome : `pine/alp0-zscore-vwap.pine` (268 lignes, `Z+VWAP v5` dans la
légende), extrait tel quel des groupes ① à ④ et des sections A et B
d'`alp0-zones.pine`. Banc : `tools/zones-pinets/zscore-vwap.mjs`
(17 contrôles). Page : https://claude.ai/artifact/7rxojTDt5ut2jV7XfADyFM.
`alp0-zones.pine` reste dans le dépôt, en sommeil.

## Hors du corpus — Option du challenge (prop)

`prop/challenge-option.html` : le challenge prop firm de l'utilisateur lu comme
une option, page autonome sombre (un `<style>`, un `<script>`, fontes Google).
Demande du 7 novembre 2026 : « graphique option animé où la prime est le prix
de mon challenge, plafond max de 4 000 $, je peux retirer seulement 50 % et
2 000 $ au plus », sur le modèle du *Strategy builder* d'options TradingView.
Page : https://claude.ai/artifact/Rh9t6JoxvBy1jspmZECW1z (v1). Un nouveau lien
à chaque amélioration : copier le fichier sous un nouveau nom.

- **Lecture retenue** : `retrait(y) = r · clip(y, 0, K)`, `K = min(plafond,
  retrait max / r)` — call spread de ratio 0,5, exercices 0 et 4 000 ; net =
  retrait − F, point mort y = F/r. Le « plafond de 4 000 $ » est lu comme le
  profit compté au plus ; avec 50 % il coïncide avec les 2 000 $. **Le prix réel
  du challenge n'a jamais été donné** : 150 $ marqué « exemple », comme le
  drawdown 2 000, l'objectif 3 000, N 20 jours, σ 450 $/j (repris de Palier).
- **Modèle** : brownien (µ, σ par jour) éteint à b = −D. Densité, survie,
  queue et valeur sont **fermées** (la valeur s'intègre sans quadrature :
  `V = G(x+µτ) − e^{2µ(b−x)/σ²} G(2b−x+µτ)`), ce qui supprime l'effondrement de
  précision près de l'échéance prévu par le plan initial. Évaluation sans
  limite de temps : `(e^{2µD/σ²} − 1)/(e^{2µD/σ²} − e^{−2µa/σ²})`, D/(D+a) à µ = 0.
- **Ce que la page affiche** : figure 1 animée (payoff rouge/vert, valeur en
  tirets bleus qui rejoint le payoff, densité orange amputée des trajectoires
  éteintes, bande de trajectoire sous l'axe sur la même échelle de profit,
  traces des courses précédentes) ; tuiles façon TradingView ; figure 2 =
  surface 3D de la valeur (profit × jour), nuage de points, coupe du jour et
  trajectoire posées dessus ; « le prix du challenge » = verdict calculé,
  tableau plancher fixe (fermé) contre plancher trailing (Monte Carlo :
  plancher = min(plus haut de clôture − D, 0), touché en séance, objectif à la
  clôture) et figure 3 (valeur du challenge selon µ, µ* aux croisements).
- **Résultat à l'exemple, µ = 0** : compte financé 384 $ (fixe) / 355 $
  (trailing) ; évaluation 40 % / 26 % ; challenge 154 $ / 92 $ pour 150 $ ;
  µ* = −1 $/j (fixe), +18 $/j (trailing). Un seul retrait compté : la suite du
  compte ne peut qu'ajouter de la valeur, la perte restant bornée au prix.
- **Contrôles** : `node tools/challenge-option/controle.mjs` extrait le bloc
  `MODELE:DEBUT … MODELE:FIN` de la page et le vérifie (90 contrôles, 3 s) :
  fermé contre Simpson, contre Monte Carlo à pont brownien (exact pour la
  surveillance continue), cas fermés à µ = 0, monotonies, µ*, trajectoires
  communes. `node tools/challenge-option/rendu.mjs [dossier]` récupère les
  vraies fontes par npm et balaie 360 → 1 280 px (erreurs, défilement, hors
  cadre, animation, Monte Carlo rendu).
- **Pièges** : `text-transform: uppercase` change « µ » en « M » et « σ » en
  « Σ » — toute lettre grecque d'un intitulé passe par `<span class="gr">`.
  Les trajectoires communes (graine égale d'une dérive à l'autre) rendent les
  écarts Monte Carlo corrélés entre dérives : un écart de 2 erreurs types aux
  trois µ est **un seul** tirage, pas un biais (vérifié sur dix graines).
  Depuis le bloc-notes, `import 'playwright'` échoue en ESM : passer par
  `createRequire`. Un script à `${…}` écrit par heredoc déclenche le garde-fou
  de suppression : l'écrire avec l'outil d'écriture.

**v2 — simulateur LucidFlex 50K** (8 novembre 2026) : `prop/challenge-option2.html`,
https://claude.ai/artifact/4W27dgJoKnkYwnW7MQRLwA. **Le compte de l'utilisateur est une
LucidFlex 50K payée 70 €** (taux € → $ réglable, 1,12 par défaut : dernière cote datée
trouvée, 11 octobre 2026). Demande : « les meilleurs outils quant, Monte Carlo, Sharpe,
Sortino… tout pour simuler les conditions réelles ».

- **Règles relevées sur des sites tiers** (le site de Lucid ne se résout pas depuis le
  conteneur : WebFetch échoue, WebSearch passe) : objectif 3 000, meilleur jour ≤ 50 % du
  profit à la réussite, drawdown 2 000 sous le plus haut de **clôture**, bloqué à +100 dès
  un plus haut de 2 100 ou dès la 1re demande ; financé : 5 jours ≥ 150 $ par cycle, profit
  du cycle > 0, demande = 50 % du profit, 500 à 2 000 $, partage 90/10 ; commissions 1 $
  (MNQ) / 3,50 $ (NQ) A/R ; 4 NQ / 40 MNQ. **Deux points divergent entre sources** et sont
  réglables : plancher touché en séance ou à la clôture, blocage à la 1re demande.
- **Moteur** (`simCompte`, bloc MODELE) : jour par jour, trade par trade (taux de gain, R:R,
  stop, contrats, commission, glissement sur stop, recul uniforme d'un gagnant avant son
  objectif, stop / objectif journaliers) ou journal collé rééchantillonné (creux de séance
  par pont brownien). Loi nulle = même stratégie au taux sans avantage (frais compris), ou
  journal recentré, **sur les mêmes tirages**. Politique de retrait : dès que possible / au
  plafond. Vue option conservée : payoff avec la **marche** de la demande minimale
  (L = 500 / r = 1 000), partage 90 %, valeur fermée généralisée.
- **Résultats à l'exemple** (MNQ ×4, stop 20, 1,5 R, 45 %, 2 trades/j, µ ≈ +30 $/j) :
  +775 $ net par challenge, 44 % de challenges payés ; **attendre 2 000 $ avant chaque
  demande : +1 401 $** (un retrait précoce bloque le plancher à +100 avec ~400 $ de marge) ;
  plancher à la clôture plutôt qu'en séance : +1 000 $ ; loi nulle : +56 $ (perte bornée au
  prix). Sharpe vrai 1,66 mais 245 jours (MinTRL) pour l'affirmer à 95 % ; recul ≥ 2 000 $
  dans 86 % des années sans blocage.
- **Contrôles** : `node tools/challenge-option/controle-lucid.mjs` (40 contrôles : chemins
  déterministes calculés à la main — réussite au jour 15, retraits aux jours 20…40 et leurs
  montants, extinctions, trailing, blocage, cohérence, séance / clôture —, moments de la
  stratégie, PSR calibré sous la loi nulle à 5,2 % ± 0,6) ; `controle.mjs
  prop/challenge-option2.html` (les 90 de la v1, toujours valides) ; `rendu.mjs` vise
  désormais la v2 et lit le curseur du jour.
- **Pièges v2** : deux fonctions `frame` (figures et boucle) — la seconde écrasait la
  première ; `Intl.NumberFormat` écrit « -0 » pour −0 (graduations à 0 : `+0`) ; la barre
  « aucun retrait » d'un histogramme à intervalle de centre positif se peignait en vert ;
  **une figure hors écran n'est pas dessinée** (économie voulue) : son en-tête ne bouge
  plus, le banc doit lire le curseur, pas l'en-tête.

**v3 — l'application** (8 novembre 2026) : `prop/challenge-option3.html`,
https://claude.ai/artifact/5iAXcZHEHGpikWuM87XPes. Demande : « énormément de texte, rends
l'app ergonomique, simple d'utilisation, organisée, avec une police propre ». **Même bloc
MODELE que la v2, recopié à l'identique** (les 130 contrôles passent sur la v3) ; seule
l'interface change :

- Cinq onglets routés par le hash (`#resultat`, `#reglages`, `#option`, `#quant`, `#carte`),
  barre en bas sur téléphone, en haut au-delà de 900 px. Résultat = gros chiffre, quatre
  indicateurs, comparaison en barres (ta stratégie / autre politique de retrait / sans
  avantage), issues, un graphique à bascule (trésorerie / comptes / gains). Réglages =
  curseurs pour les cinq leviers, trois bascules de règles, le reste replié dans
  « Réglages avancés ». Le modèle, les formules, les définitions et les sources sont dans
  une fenêtre (`<dialog>`) ouverte par le bouton « i ». Plus aucune légende longue.
- Police **Geist** (Google Fonts, chargée par `next/font/google` chez Vercel, donc servie
  par Google) et Geist Mono pour les graduations ; repli système propre.
- `rendu.mjs` lit désormais les familles demandées par la page, les récupère par npm
  (`@fontsource/geist-sans`, `geist-mono`…) et balaie **chaque onglet** à six largeurs.
- **Pièges v3** : une règle d'auteur `.view{display:flex}` l'emporte sur l'attribut
  `hidden` — les cinq vues restaient empilées dans l'aperçu (le gabarit des artefacts
  ajoute `[hidden]{display:none!important}`, l'aperçu local non) : la règle est posée dans
  la page ; l'espace fine insécable (U+202F) des milliers est presque invisible en Geist
  (« +1401 $ ») : remplacée par U+00A0 ; l'outil d'écriture transforme `\u202f` en
  caractère littéral, un remplacement Python doit viser le caractère ; une figure d'un
  onglet caché se construit à 0 px de large : on ne construit que la vue affichée, à
  l'ouverture de l'onglet.

**v4 — leviers** (8 novembre 2026, « carte blanche pour tout améliorer ») :
`prop/challenge-option4.html`, https://claude.ai/artifact/EsTvvxGHHeDZcYtTsoAPwr.
L'onglet Carte devient **Leviers** : taille optimale (gain net et part payée selon le nombre
de contrats, échelle log, 2 000 challenges par point sur les mêmes tirages), tornade de
sensibilité (taux de gain ±2,5 pts, ratio ±0,25 R, contrats ±1, trades/jour ±1, glissement
0 / +2 ticks, autre politique de retrait), puis la carte et son relief. Réglages : bandeau de
résultat collant qui suit les curseurs. Barre de progression sous l'en-tête. Rappel quand
les chiffres viennent de l'exemple. Gain par jour de bourse (`tMoy` ajouté au modèle :
durée moyenne d'un challenge). Kelly et risque par trade traduits en dollars sur le
drawdown. À l'exemple : la taille optimale est 4 MNQ (+782 $) ; à 6 MNQ, +727 $ mais 28 %
de challenges payés au lieu de 44 %, et la loi nulle monte à +91 $ (le payoff borné
récompense la variance). Calcul complet ≈ 1,8 s.

**v5 — noir, blanc, gris, animée en continu** (8 novembre 2026, « améliore à fond l'ux design
de l'app noir blanc gris avec animation constante et fluide ») : `prop/challenge-option5.html`,
https://claude.ai/artifact/R9m5xQUxyvNS2DSWeEPVBK. **Bloc MODELE identique à la v4**
(vérifié par `diff`, 130 contrôles passés) ; seuls le style et le mouvement changent.

- **Monochrome strict, la forme porte le sens** : gain = blanc plein, perte = gris hachuré
  (motif `#hx` d'un SVG caché en tête de `<main>`, partagé par toutes les figures), valeur =
  tirets clairs, densité = pointillés (`#dt`), loi nulle = gris sombre. Reliefs 3D : carrés
  pleins si positif, vides si négatif. Carte : blanc de plus en plus plein / hachures de plus
  en plus nettes. Issues : pertes hachurées, retraits du gris clair au blanc.
- **Une seule boucle `requestAnimationFrame`** pilote tout, et ne fait avancer que ce que
  l'`IntersectionObserver` voit : fond du résultat (évaluations jouées en direct, `Walker` /
  `stepW`, mêmes journées `ST.dayF` et même plancher que `simCompte`, masquées à gauche pour
  laisser lire le chiffre), aperçu en direct dans les réglages (un compte, son plancher en
  escalier, l'objectif, compteur réussies / tentées), trésorerie qui rejoue un challenge tiré,
  comptes qui passent au premier plan à tour de rôle, un « tirage » qui glisse sur les trois
  histogrammes (`mkSampler`), reliefs en balancement continu (amplitude 0,33 rad : à 0,45 les
  étiquettes d'axe se chevauchaient). **Ces animations illustrent ; tous les chiffres viennent
  du Monte Carlo.**
- Chiffres qui glissent (`tween`), barres de comparaison et segments d'issue qui changent de
  longueur au lieu d'être reconstruits, indicateurs glissants sous les onglets et dans chaque
  bascule (`placeInd`, `<i class="ind">` injecté en tête de chaque `.seg`), entrée en cascade
  des cartes, tracés déroulés de gauche à droite (`reveal`, clip-path 1,1 s) à l'ouverture
  d'un onglet et à l'arrivée de nouveaux résultats — pas au redimensionnement.
- `prefers-reduced-motion` : tout s'arrête, le fond et l'aperçu sont pré-calculés en une image
  fixe déjà remplie.
- **Contrôles** : `controle.mjs` et `controle-lucid.mjs` sur la v5 ; `rendu.mjs` vise la v5 par
  défaut ; **nouveau `node tools/challenge-option/vivant.mjs <dossier de rendu.mjs> [largeur]`** :
  captures après 9 s d'animation, images/s pendant la rotation (61 mesurées), aperçu qui
  compte, puis chaque onglet en mouvement réduit (aucune erreur, fond déjà dessiné).
- **Pièges v5** : un marqueur créé hors écran n'est jamais avancé (la boucle ne travaille que
  sur le visible) et restait en (0, 0) — chaque figure place son marqueur à la construction
  (`tick3(0)`, `tickSamp(sp, 0)`) ; les captures de `rendu.mjs` tombent 700 ms après le
  changement d'onglet, pendant le déroulé de 1,1 s : une graduation de droite tronquée
  (« J25 ») y est normale ; une case de carte faiblement positive (blanc à 12 %) se lisait plus
  sombre qu'une case négative grise — d'où les hachures pour les pertes ; un intitulé « en
  direct » trop long passait sur deux lignes à 390 px.

**v6 — couleurs de sens, graphiques fluides** (8 novembre 2026, « pour des data qui nécessitent
une couleur tu peux ajouter vert rouge ou orange ; améliore les graphiques ») :
`prop/challenge-option6.html`, https://claude.ai/artifact/Ftr4oSF9pCxmXwX2u2BqYu. Vert = gain,
rouge = perte ou extinction (toujours doublé de hachures, pour qui confond rouge et vert),
orange = alerte (seuil de drawdown, plancher à moins d'un quart du drawdown) ; tout le reste
reste noir, blanc, gris. Réticule lissé par la boucle (`HOV`, cible et position), fondu
enchaîné quand les données changent (`clearSvg` : l'ancienne figure passe au-dessus dans un
`g.old` qui s'efface ; une figure vide se déroule ; rien au redimensionnement, drapeau `NOFADE`),
graduations à 11 px (marges gauches 50 / 60 px, `CH = 11 × 0,6`), étiquettes de la tornade
rangées dans leur barre quand elles sortiraient, fond du résultat déjà peuplé (`ambStep` ×80).

**v7 — nouveautés** (même jour, « ajoute des nouveautés utiles ») : `prop/challenge-option7.html`,
https://claude.ai/artifact/CGhKxvJrT8YQjihU2D9i21. Sixième onglet **Compte** (`#compte`) : l'état réel du jour (profit, plus haut de
clôture, jours tradés, meilleur jour ; en financé : jours qualifiants, plancher bloqué) donne le
plancher, la marge, les pertes d'avance, l'objectif porté par la règle du meilleur jour
(max(objectif, meilleur jour / 50 %)), une jauge animée plancher → objectif, 3 000 suites
simulées depuis aujourd'hui, et les contrats max pour garder k pertes d'avance. Carte **Mon
budget** (résultat) : n = budget / prix, au moins un payé = 1 − (1 − p)^n, total par 2 000 sommes
tirées dans le Monte Carlo, courbe et seuil de 90 %. **Épingler** un réglage (localStorage
`alp-option-challenge-pin-v7`) : écart dans le bandeau et dans Comparer, bouton pour le
rappeler. **Copier le résumé** (presse-papiers dans le clic, sinon texte sélectionné).
- **Le bloc MODELE change pour la première fois depuis la v2** : `simCompte(…, e0)` repart d'un
  état ; sans `e0` le moteur est inchangé (90 + 40 contrôles toujours verts). Sept contrôles
  ajoutés à `controle-lucid.mjs` (sautés sur les pages plus anciennes) : l'état de départ
  redonne le moteur sans état, prix mis à part ; réussite au jour 1 depuis 2 800 $ ; règle du
  meilleur jour (1 600 $ impose 3 200 $) ; financé neuf = retraits du contrôle 1 décalés de
  quinze jours ; plancher bloqué à +100 contre plancher à −500.
- **Piège** : `console.log` lit « %s » dans une chaîne affichée (« 85 %sans avantage ») comme un
  format et y injecte l'argument suivant — un banc qui imprime du texte de page doit le passer
  en second argument.

**v8 — leviers compréhensibles, paramètres qu'on cache et qu'on rouvre** (8 novembre 2026,
« je comprends pas les graphiques dans levier ; pouvoir cacher les paramètres et les revoir
grâce au bouton » puis « améliore la qualité surtout de l'app ») : `prop/challenge-option8.html`,
https://claude.ai/artifact/VgWxRVU9Vj9J72TUCC84Gs. Bloc MODELE identique à la v7 (`diff`),
137 contrôles verts.
- **Leviers** : chaque graphique est une question (« Combien de contrats ? », « Quel réglage
  pèse le plus ? », « Quel taux de gain pour quel ratio ? ») avec **la réponse calculée écrite
  au-dessus** (`#lv-ans`, `#tor-ans`, `#ca-ans` ; `seuilCarte(rr)` interpole la frontière du
  challenge au ratio de l'utilisateur) et une explication que le bouton « ? » cache ou rend.
  Contrats : colonnes alignées sur deux étages (gain net, part payée), taille actuelle cerclée,
  meilleure en vert plein — plus d'échelle log. Tornade : **écarts au réglage actuel**, une
  barre par sens, la valeur au bout, le cran de l'autre côté ; étiquettes au-dessus des barres
  sous 560 px. Carte : « rentable », « perdant », « seuil du challenge », « toi +775 $ » posés
  sur la figure. Relief replié derrière « Afficher ».
- **Un seul « toi »** : les leviers (2 000 challenges, mêmes tirages) sont ancrés sur le
  résultat principal (`adjE`, `adjP` : niveau du Monte Carlo à 5 000, écart des leviers) — la v7
  affichait +782 $ dans Leviers et +775 $ partout ailleurs pour le même réglage.
- **Bouton Paramètres** dans l'en-tête : panneau (`#sheet`, en bas sur téléphone, à droite
  au-delà de 900 px) avec instrument, cinq curseurs (`q-*`, tenus avec `r-*` par
  `syncSliders`), politique de retrait et résultat en direct ; croix, « Masquer », Échap.
  Fermé, il porte `hidden` (sinon, translaté hors écran, le balayage le compterait hors cadre).
- **Cartes repliables** (Ta stratégie, Règles du compte, Mon compte aujourd'hui) : flèche,
  résumé d'une ligne qui rouvre au toucher, état gardé (`alp-option-challenge-ui-v8`).
- **Banc** : `node tools/challenge-option/panneau.mjs <dossier de rendu.mjs> [largeur]` —
  18 contrôles dans le vrai navigateur (« ? », relief dessiné, réponses écrites, panneau qui
  recalcule les leviers depuis l'onglet Leviers, curseurs jumeaux, Échap, cartes repliées
  gardées après rechargement), verts à 390 et 1 280 px ; `vivant.mjs` déplie le relief.

**v9 — le temps et le calendrier** (8 novembre 2026, « améliore tout et s'il faut ajouter
ajoute ») : `prop/challenge-option9.html`, https://claude.ai/artifact/GjneqAbWMrGthpCrnYHXJK.
- **Le moteur garde le calendrier de chaque challenge** : `tP` (jour de réussite), `t1`
  (1er retrait), `tKo` (extinction), −1 pour jamais ; rien d'autre ne change. Six contrôles de
  plus dans `controle-lucid.mjs` (53) : J15 / J20 / jamais à +200 $ par jour, J7 à −300 $,
  financé bloqué éteint J5, comptes cohérents sur 2 000 challenges.
- **« Dans le temps »**, première vue de la simulation du résultat, et **« Jour après jour »**
  dans Compte (depuis l'état du jour) : quatre états empilés, payé (vert), financé sans retrait
  (vert pâle), en évaluation (gris), perdu (rouge hachuré) ; `timeline(r, H)` s'arrête quand
  97 % des challenges sont tranchés ; réponse écrite au jour 20 (Compte) ou 60 (résultat).
- **Dates** : `dateTxt(n)` compte n jours ouvrés (samedi et dimanche sautés, fériés non) à
  partir d'aujourd'hui — réussite et 1er retrait médians datés dans Compte, info-bulles datées.
- **Plafond du jour** (règle du meilleur jour) : au-delà de 50 % × objectif effectif gagnés en
  un jour, l'objectif monte — dit sous « Reste à gagner ».
- **Bien démarrer** : carte en trois étapes en tête du résultat (paramètres, résultat, compte),
  fermée une fois pour toutes (`UI.intro`) ; le rappel « chiffres d'exemple » ne vient qu'après.

**v10 — le journal du soir, et chaque onglet répond** (8 novembre 2026, « améliore tout, carte
blanche ») : `prop/challenge-option10.html`, https://claude.ai/artifact/878witkZZ6yLD7w33eRm43. Bloc MODELE identique à la v9.
- **Ma journée** (Compte) : on tape le P&L du soir, `addDay` met à jour profit, plus haut de
  clôture, jours, meilleur jour et jours qualifiants (≥ `qmin`, en financé) ; chaque journée
  garde l'état d'avant, d'où une annulation exacte (`undoDay`) ; effacement en deux touchers ;
  courbe réelle avec plancher qui suit (recalculé dans les états gardés), objectif ou retrait
  minimal, points verts / rouges. Historique à part (`alp-option-challenge-hist-v10`) :
  « revenir à l'exemple » ne l'efface pas.
- **Option et Quant** prennent la forme des Leviers : une question pour titre, la réponse
  calculée (`#ao1`, `#aq1` à `#aq3`), une explication derrière « ? ». Les explications marquées
  `data-def="0"` sont fermées à la première visite (cartes d'indicateurs), les autres ouvertes.
- **Banc** : `panneau.mjs` ajoute 8 contrôles (trois journées → 250 / 300 / 3 / 300, annulation
  → 100 / 2 jours, effacement à confirmer, réponses d'Option et de Quant), soit 26.

**v11 — la matière et la lumière** (8 novembre 2026, « améliore encore surtout le visuel à
fond ») : `prop/challenge-option11.html`, https://claude.ai/artifact/EDk2d1ZvTAVeZ7UNr4EbVS. Bloc MODELE identique à la v9 ; seul le
style change, plus deux fonctions d'affichage (`ring`, `kpiRC`).
- Fond à halos (blanc en haut, vert en bas à gauche) et trame de points fixe ; trait de
  lumière sous l'en-tête ; cartes à liseré dégradé (`padding-box` / `border-box`, sauf
  `.banner` et `.intro` qui gardent leur fond) ; grand chiffre en dégradé avec halo de son
  signe (`--hg`, vert ou rouge, posé par `renderHero`) ; anneaux de progression sur les
  pourcentages (payés, évaluation, réussite, au moins un retrait, budget) ; lueur `#glow` sur
  les courbes principales ; grilles pointillées ; info-bulles en verre dépoli.
- **Piège** : un filtre SVG en unités de boîte englobante efface une ligne parfaitement
  horizontale (hauteur nulle) — la médiane de trésorerie l'est souvent. `#glow` est en
  `filterUnits="userSpaceOnUse"`. Et `text-shadow` sur un texte en `background-clip:text` se
  peint par-dessus le dégradé : le halo du grand chiffre passe par `filter: drop-shadow`.

**v12 — des leviers qui disent quoi faire** (8 novembre 2026, « améliore l'espace levier ») :
`prop/challenge-option12.html`, https://claude.ai/artifact/N9soyjwz1i95z2uSXnUKC5. Bloc MODELE
identique à la v9.
- **« Que changer dès demain ? »** en tête des Leviers : les leviers que l'utilisateur
  contrôle (meilleure taille, autre moment de retrait, ±1 trade par jour, meilleure limite
  journalière), écarts sur les mêmes 2 000 challenges, rangés par gain (au moins 5 $), trois
  au plus, chacun avec **Appliquer** (change le réglage, relance tout). Le ratio et le taux
  de gain n'y figurent pas : le modèle tient le taux fixe quand le ratio bouge, ce qui serait
  un conseil faux.
- **« Faut-il une limite journalière ? »** : `limVariants(S)` — aucune, arrêt après 1 perte,
  après 1 gain, après 1 perte ou 1 gain (et 2 pertes / 2 gains dès 3 trades par jour) ;
  `dStop = Lo`, `dTgt = W` de `tradeStats`, que `journee` lit déjà ; 2 000 challenges par
  règle dans `MC.lev.lim` ; ligne actuelle marquée, Appliquer sur les autres. **Piège** :
  arrondir la limite au centime vers le haut l'empêche de se déclencher pile à une perte
  (−166,125 > −166,13) : `applyLim` arrondit vers le bas.
- `panneau.mjs` : trois contrôles de plus (réponse des gestes, règles comparées, Appliquer
  pose la limite et marque la ligne actuelle). Ses captures gardent les réglages laissés par
  ses propres essais (taux de gain à 50 %) : pour une capture « exemple », vider le stockage.

**v13 — les graphiques au style du Strategy builder** (8 novembre 2026, capture du tutoriel
Options de TradingView, « améliore les graphiques dans ce style, pas le graphique en lui-même ») :
`prop/challenge-option13.html`, https://claude.ai/artifact/4GSqY8p8iXDXAGfD143CnY. Bloc MODELE
identique à la v9 ; seuls les couleurs et le
style des figures changent.
- **Palette TradingView** : sarcelle `#22c39b` (gain), rose `#f0476b` (perte), orange
  `#f7a35c` (alerte et densité), bleu `#6f7cff` (valeur) — remplacées partout, y compris dans
  les motifs, dégradés et `rgba` écrits dans le script.
- **Panneau par graphique** : `data-pill="…"` sur les quinze `.plot` (pastille en haut à
  gauche par `::before`, `padding-top: 48px` — seulement vertical, pour que `clientWidth`
  reste la largeur du dessin) ; fond `--panel`, lueurs rose / sarcelle / orange dans le payoff,
  le temps et les cartes ; `.bgp` transparent ; grille fine pleine ; graduations en Geist ;
  courbes à 2,7–3 px ; valeur en pointillés bleus, densité en tirets orange ; curseur en
  tirets ; marqueurs cerclés du fond du panneau. Les explications qui nommaient « tirets » et
  « pointillés » ont suivi l'échange des deux.

**v14 — plus calme, façon 2026** (8 novembre 2026, « rends l'app plus clean avec une UX type
2026 ») : `prop/challenge-option14.html`, https://claude.ai/artifact/RUpU9ZjbLC8fgsXRNrWvo4.
Bloc MODELE identique à la v9 ; une couche CSS
« v14 » en fin de feuille, et deux retouches : `gOn` replie toutes les explications par défaut
(`data-def="1"` pour en ouvrir une), le paragraphe d'introduction des Leviers est retiré.
- Barre d'onglets du téléphone **flottante** : capsule de verre détachée des bords (12 px,
  10 px + zone sûre), indicateur en pilule ; fond sans trame, un seul halo ; en-tête en verre
  sans trait de lumière ; cartes plates à liseré de 6 % ; commandes, bascules, champs et
  boutons en pilule ; indicateurs sans bordure.
- `panneau.mjs` vérifie désormais que « ? » bascule l'explication et la remet comme avant,
  quel que soit son état de départ.

**v15 — Monte Carlo instantané dans le payoff** (8 novembre 2026, « simuler 100, 1 000,
10 000 fois au lieu d'attendre en live ») : `prop/challenge-option15.html`,
https://claude.ai/artifact/7dWezqGp8N7a6A33ZT7fph. Bloc MODELE identique à la v9. Sous le payoff : « Simuler d'un coup » 100 / 1 000 /
10 000 et Lancer (`runMC1`) — n comptes financés, plancher fixe, pas journaliers et pont
brownien comme la formule, graine fixe ; la lecture se met en pause au jour 0, l'histogramme
du profit au jour N (roses sous le point mort, sarcelle au-dessus) se pose sous la cloche
orange avec la même normalisation (`σ√N·√(2π)`), 80 trajectoires dans la bande ; le texte
compare éteints, au-dessus du point mort et retrait moyen ± 2 erreurs types à la formule.
Relancer la lecture ou changer un réglage efface la simulation. `panneau.mjs` : un contrôle de
plus (46 barres, 80 trajectoires pour 10 000 comptes).

**v16 — Monte Carlo animé, reliefs pleins, surface de décision** (8 novembre 2026, trois
captures : carte satellite à réticules, classifieur k-NN, surface 3D « Marius ») :
`prop/challenge-option16.html`, https://claude.ai/artifact/1y45h71sQ8RTAaP6tFxzpP. Bloc MODELE
identique à la v9.
- Monte Carlo du payoff : trajectoires tracées à la chaîne (`pathLength=1`, retard 14 ms
  chacune), barres qui montent (`scaleY`, retard 12 ms).
- **Reliefs pleins** (`Surf3D`) : facettes peintes du fond vers l'avant, teinte `turbo` selon la
  hauteur, sept courbes de niveau projetées au sol (marching squares), échelle de couleur à
  droite ; la coupe du jour passe en blanc. Les surfaces de ce fichier ne sont plus des nuages
  de points — la règle contraire vaut pour ALP nº 3, pas pour l'app.
- **« Où est-on payé ? »** (Leviers, `draw18`) : fond = probabilité d'être payé interpolée
  (rose → sombre → sarcelle), **points = vrais challenges simulés** de chaque case (36 sur 250,
  `paid` lu dans `t1`, position tirée dans la case), frontière de rentabilité en tirets,
  étoile « toi » et P(payé), explication derrière « ? ».
- Relevés cartographiques discrets (`data-hud`, mono 9 px, majuscules sans lettre grecque) sur
  le payoff, les reliefs, la carte, la surface de décision et les vues Monte Carlo ; trame de
  croix sur le résultat, les reliefs et la surface de décision.

**v17 — retouches** (8 novembre 2026, « pas d'étoile, juste un point ; un texte gêne en arrière-plan ») :
`prop/challenge-option17.html`, https://claude.ai/artifact/3Jod1oZ1TDsju7j1qHgGCL. Point blanc cerclé au lieu de l'étoile dans la surface de
décision ; relevé du résultat (`#hero-hud`) retiré. **Piège** : la règle
`.hero>*:not(canvas){position:relative}` l'emportait sur `.hud3{position:absolute}` — le relevé
tombait dans le flux, en haut à gauche, sur l'intitulé. Tout enfant ajouté au héros hérite de
cette règle.

**v18** (8 novembre 2026, « enlève la surface de décision ; le texte des graphiques n'est pas
beau, mets-le sur un encadré ») : `prop/challenge-option18.html`, https://claude.ai/artifact/EaK49KsccHvmZvgfmnGAii, **dernière version, c'est elle
qu'on améliore**. Carte « Où est-on payé ? » retirée (`draw18` reste, inerte sans `#c18`).
`boxLabels(svg)` pose un encadré sombre arrondi (`rect.labbox`) sous chaque `text.lab`, deux
images après la construction (`clearSvg` le programme) ; sautés : les textes qui changent à chaque
image (`F1.ko`, `F1.lt`, `F3.lx`, tirages `.smk`).

## Mémoire détaillée — à lire À LA DEMANDE, pas en bloc

Le détail a été déplacé dans `docs/memoire/` pour que chaque session ne paie pas
~35 000 tokens de contexte avant de commencer. **Règle : lire le fichier qui
correspond à ce qu'on touche, avant de le toucher** — jamais le dossier entier.

- `docs/memoire/parties-xiv-a-xxx.md` — détail des parties XIV à XXX d'ALP nº 3 (résultats, pièges enterrés de chacune). À lire pour toute retouche d'une de ces parties.
- `docs/memoire/carte-des-modules.md` — rôle de chaque module Python, des `fig*.py` et des fichiers Pine. À lire avant de modifier un module.
- `docs/memoire/pieges.md` — pièges de graine, circularité, bornage, chevauchement, sommaire figé, rendu des figures, trois balayages. **À lire avant toute retouche de figure ou de gabarit.**

Pièges (titres seulement ; le corps est dans `pieges.md`) :

- Le `hash` intégré n'est pas une graine
- La circularité — le pire, et il a survécu longtemps
- Le bornage `max(2.0, budget)` — retiré partout, ne pas le remettre
- Le chevauchement des fenêtres — trois cents chemins comptés mille fois
- La divergence figure/table
- Le sommaire figé — trois parties portées par le corps, absentes de la table
- L'échantillon
- Le paramètre non observable qui décide de la loi nulle
- Les surfaces sont des nuages de points, plus des mailles
- Le domaine écrit à la main — retrouvé huit fois
- Une légende écrite devant un cadre borné décrit le bornage — six fois
- Une figure doit montrer ce que la section décrit
- Le libellé ARIA ne peut porter aucune apostrophe
- Une bande peinte après les barres qu'elle commente
- Une planche qui trace une série sous l'intitulé d'une autre
- Un texte barré par un tracé ne se voit à aucun balayage
- Une constante fausse qu'aucune relecture n'attrape
- Une graduation hors domaine ne se voit dans aucun balayage
- Un relief à trop grande dynamique ne montre plus rien
- Quatre courbes de la même rampe sont quatre courbes indistinguables
- Un relief dont la hauteur est une transformée
- Les pièges de rendu
- Les trois balayages, à rejouer après toute retouche de figure

Parties détaillées dans `parties-xiv-a-xxx.md` : XIV à XXX (une par module `<nom>.py` + `fig<abrégé>.py`).

## Suivi du contexte — règle de session

**Piège (7 novembre 2026)** : `context_usage` a renvoyé 0 pendant presque
toute la session ; les pourcentages annoncés à l'utilisateur étaient des
estimations, et fausses (« ≈ 45 % » quand le vrai chiffre approchait 80 %).
Ne jamais annoncer un pourcentage sans un `used_tokens` non nul ; sinon dire
qu'il est inconnu.

À chaque réponse, indiquer le pourcentage de contexte utilisé (outil `get_session`, champ `context_usage`). **À 60 %** : prévenir et proposer `/compact`. **À 80 %** : dire « critique », commiter et pousser le travail en cours, mettre à jour ce fichier si un fait nouveau est établi, puis demander à l'utilisateur de lancer `/clear` et de relire ce fichier. Ne pas lancer la suite complète de tests (≈85 min) : seulement le test du module touché.

## La direction artistique du document nº 3

Trois règles, et elles se tiennent.

**Un seul accent, et c'est celui des planches.** `--accent: #9B8CFF` est
**exactement** le `--s1` de `figcss.py` en fond sombre. Il porte le numéro
d'une partie, celui d'une section, celui d'une table ou d'une figure — et
rien d'autre. Le document et ses figures cessent ainsi d'être deux objets :
le numéro « Figure 6 » a la teinte de la courbe qu'il commente. Jamais plus
de trois occurrences par page ; une couleur qui se répète cesse d'accentuer.

**Un lever de partie est une respiration, pas un titre plus gros.** La barre
pleine largeur qui l'ouvrait le *barrait* — elle fermait la page précédente
au lieu d'ouvrir la suivante. Un filet court de 2,6 rem en accent fait
l'inverse. Le titre de partie est à 2,35 rem contre 1,46 pour une section :
il faut **entendre la marche**, sinon seize parties et soixante-six sections
se lisent comme une seule masse.

**La marge n'est pas une perte.** Au-delà de 74 rem, le numéro de section
descend dans le blanc de gauche, en chasse fixe et en accent : la ligne de
titre se libère. En dessous il revient dans le fil, ce qui évite tout
débordement. Le chapeau d'une partie est en italique, **non justifié et non
césuré** : trois lignes coupées sur un motif de césure se lisent comme un
accident de mise en page.

## Commandes

```
python main.py --tests      # ~1990 tests (compter ~85 min ; --wp, setups,
                            # robustesse, overnight, emprunts, revue,
                            # niveaux, theta et vega sont lents)
python main.py --wp         # reconstruit docs/temps-de-marche-et-peremption.html
python main.py --paper      # reconstruit docs/alp1-paper.html (version courte)
python main.py --discpaper  # reconstruit docs/prouver-un-jugement.html
python main.py --strategy   # rejoue la stratégie scellée et sa batterie
python main.py --bounds     # la mesure encadrée par les deux remplissages
python main.py --disc       # journal de décision, lois nulles, attribution
```

Modules exécutables directement pour inspecter leurs chiffres :
`python -c "from alp1 import footprint; footprint.main()"` — idem pour `tpo`,
`spectrum`, `seuil`, `report11`, `report14`, `concepts`, `setups`,
`emprunts`, `fonds`, `theta`, `vega`.

## Contraintes d'environnement

Le réseau sortant ne joint que les registres de paquets et GitHub : **aucun
hébergeur de données de marché n'est atteignable**. Toute mesure se fait donc
sur série synthétique de vérité connue, ou sur un fichier fourni par
l'utilisateur au format décrit dans `docs/donnees-requises.md`.

Chromium est préinstallé et Playwright le trouve — ne jamais lancer
`playwright install`.

Développement sur la branche `claude/project-main-file-l8ix6k`. Ne jamais
pousser ailleurs sans autorisation explicite. Pas de pull request sauf demande
explicite.

## Ce que l'utilisateur demande, en continu

- Un **nouveau lien d'artefact à chaque amélioration**, jamais une republication.
- Le **pourcentage de tokens restant** à chaque réponse.
- Français, ton neutre et objectif, mais des phrases qui donnent envie de lire.
- Fond sombre, langage graphique des captures « Marius Alpha Engine ».
- **Chaque concept doit être imagé**, en 2D *et* en 3D, avec les meilleures
  données possibles et une variété de types de graphiques.
- Carte blanche pour retirer ce qui est faux.

## Arbitrages ouverts — non tranchés, ils engagent le nom de l'auteur

1. Adopter le test directionnel : 39 % de trades en moins, mais impose un
   re-scellement du protocole préenregistré.
2. Remplacer le ratio de variance par la DFA dans le Test 1. **Le défaut qui
   motivait cet arbitrage est corrigé** : le critère de passage se lisait
   « Ĥ significativement supérieur à 0,5 » alors que l'estimateur rend
   0,5182 ± 0,0031 sur une vraie martingale — six écarts-types, donc un test
   franchi par le bruit seul. Le protocole se lit maintenant contre la loi
   nulle simulée de l'estimateur, que `report5` publie déjà. Reste la question
   ouverte, plus faible : la DFA serait-elle un meilleur estimateur que le
   ratio de variance corrigé ? Elle ne corrige pas un test faux, elle en
   choisirait un autre.
3. Recalculer le chapitre des instruments à c = 0,65 au lieu de 0,33 —
   cela publierait des chiffres nettement moins favorables.
4. Points d'audit 4, 5 et 6 : câbler la batterie anti-surajustement et le
   journal d'exécution dans `measure.py`.
5. ALP nº 1 porte toujours sa dérive de référence circulaire **dans les
   chiffres** de ses chapitres de risque. Ce qui a changé : sa section 18 la
   nomme, la mesure et sépare, par verdict calculé, les trois grandeurs que le
   changement d'hypothèse laisse intactes des dix qu'il emporte. Le document
   n'affirme donc plus rien de faux, mais ses tables restent chiffrées à
   `k = 2`. Les recalculer à dérive déclarée changerait des dizaines de
   chiffres publiés **et une centaine de phrases écrites devant eux** — c'est
   le piège de la légende décrite plus bas, à l'échelle d'une partie entière.
   Décision non tranchée.
