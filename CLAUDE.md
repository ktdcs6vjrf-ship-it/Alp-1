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
beau, mets-le sur un encadré ») : `prop/challenge-option18.html`, https://claude.ai/artifact/EaK49KsccHvmZvgfmnGAii. Carte « Où est-on payé ? » retirée (`draw18` reste, inerte sans `#c18`).
`boxLabels(svg)` pose un encadré sombre arrondi (`rect.labbox`) sous chaque `text.lab`, deux
images après la construction (`clearSvg` le programme) ; sautés : les textes qui changent à chaque
image (`F1.ko`, `F1.lt`, `F3.lx`, tirages `.smk`).

**v19 — tes données, ton avantage** (8 novembre 2026, nuit, « carte blanche, améliore tout, ajoute ou supprime ») :
`prop/challenge-option19.html`, https://claude.ai/artifact/WRCYGVYgp56khBSvX42nBY. Le bloc MODELE gagne neuf
fonctions pures (rien d'autre ne change : 90 + 53 contrôles toujours verts).
- **Tes données** (Réglages) : chaque lien a son stockage local, vide — la v18 ne peut donc rien transmettre. Sauvegarde
  `ALPOPT1:` + JSON en base 64 (réglages, journées, épingle, préférences), copiée (repli : texte sélectionné), recollée
  dans la version suivante ; tout ce qui est lu passe par `sanitizeP` / `okH` (clés connues, bon type).
- **Ma journée → simulation** : dès 10 journées, « Simuler avec mes journées » met le mode Mon journal sur les journées
  réelles (`histDays`) ; bouton « Reprendre mes journées » dans Mon journal. Chaque journée garde sa date (`t`).
- **« Combien de trades pour le prouver ? »** (Quant) : test binomial exact à 95 % contre le seuil sans avantage `pBE`
  (déclaré, jamais tiré du bilan jugé). Courbe = puissance du test **randomisé sur sa frontière** (taille exactement 5 %,
  sinon dents de scie de ±2 points) ; ligne grise = loi nulle ; bilan saisi (`vt`, `vw`) jugé par la p-valeur exacte,
  a posteriori bêta uniforme. À l'exemple : seuil 41,29 %, une chance sur deux à 481 trades, quatre sur cinq à 1 103.
  Banc : `node tools/challenge-option/controle-preuve.mjs [page]` (33 contrôles : lgamma, queues contre sommes directes,
  frontière et taille, Monte Carlo à 470 et 1 100 trades, a posteriori contre intégrale).
- **Étiquettes vivantes** (`dynLab` / `setDyn`) : KO, trajectoire, trésorerie rejouée et tirages ont leur encadré, mesuré
  au canevas (`textW`) ; `boxLabels` recense les encadrés fixes (`svg._boxes`) et l'étiquette d'un tirage prend la
  première ligne libre — en v18 « une mesure » couvrait « vrai +1,66 » et « une année » couvrait « drawdown ».
- Code mort retiré : `draw18`, `#ds-ans`, `paid` des cases de la carte.
- **Pièges v19** : `num(v, s, 3)` n'existait pas (`NF` s'arrêtait à 2 décimales) — la p-valeur cassait le rendu sans
  bruit visible hors console ; un banc qui compte des éléments d'une figure doit viser `svg > …` : le fondu enchaîné garde
  l'ancienne figure 0,5 s dans `g.old` ; `panneau.mjs` hérite de l'état laissé par ses propres essais (profit 100 $ après
  l'annulation) — comparer avant / après plutôt qu'à une valeur écrite.

**v20 — le calcul en parallèle** (même nuit) : `prop/challenge-option20.html`,
https://claude.ai/artifact/SGxPRqRNs9vR6fWfpXuycc. Bloc MODELE identique à la v19.
- **Bloc `TRAVAIL`** (après MODELE:FIN) : `dayOf` (journée décrite par une donnée `{k:"t",S}` / `{k:"j",J}`, jamais par
  une fonction), `runJob` (travaux `compte`, `libre`, `ev`, `cell`), `mergeCompte`, `mergeLibre`. Les workers sont faits
  d'un Blob = texte des blocs MODELE + TRAVAIL lus dans `document.currentScript` (`SRC`) : même code qu'en fil principal.
- File unique (`exec`) : workers (jusqu'à 4, `hardwareConcurrency − 1`) ou repli `mainRun` par tranches de 8 ms si
  `Worker` manque ou échoue (`poolFail` relance ici ce qui était en cours). Groupe + génération par travail : `cancelOld`
  retire de la file une génération dépassée. Découpage **fixe** (250 challenges, 100 comptes libres, 500 pour les
  leviers), fusion dans l'ordre : chiffres identiques avec et sans workers, sur toute machine.
- `canvasFit` lit la taille d'un `ResizeObserver` : `getBoundingClientRect` à chaque image forçait une mise en page
  (½ s cumulée pendant le calcul au CPU ÷4). Le résultat se rend en trois tâches (`renderResultat`, `RRT`).
- Mesures (CPU ÷4, 4 cœurs) : calcul complet 9,8 s → 3,6 s, pire image 283 ms (v19) → 83 ms ; à pleine vitesse
  2,0 s → 1,6 s (chargement compris). Banc : `node tools/challenge-option/parallele.mjs <dossier de rendu.mjs> [÷cpu]`
  — mêmes chiffres sur quatre onglets avec et sans workers, puis temps et pire image après le chargement.

**v21 — le compte réel au centre** (même nuit) : `prop/challenge-option21.html`,
https://claude.ai/artifact/WBwgrdumowgNZ6RTCiALqX. Blocs MODELE et
TRAVAIL identiques à la v20.
- **Ma journée** : date de séance (`f-jd`, `seanceISO` : avant 6 h → veille, samedi / dimanche → vendredi ; après une
  date passée, la suivante avance d'un jour ouvré, `nextDate`), trades et gagnants facultatifs (`h.n`, `h.w`, validés par
  `cleanH`, gardés dans la sauvegarde).
- **Mon calendrier** (`#et-cal`, `renderCal`) : mois de la dernière séance saisie, L–V + total de la semaine, teinte selon
  |P&L| du mois (perte hachurée), séance d'un week-end comptée avec le vendredi.
- **Tes journées contre tes réglages** (`renderChk`, dès 5 journées, mode trades seulement) : K moyennes de n journées
  tirées avec `ST.dayF` (K = 4 000, moins au-delà de 100 journées), bande 5–95 % ; hors bande → « trop optimiste » ou
  « trop prudente ». Mémoïsé par (n, moyenne, réglage, graine).
- **Rappel du compte** en tête du Résultat (`#acs`, lien `#compte`), même pastille que l'onglet Compte.
- Preuve du taux de gain : « Reprendre mes journées » remplit le bilan avec les trades comptés.
- **Pièges v21** : le calendrier restait sur le premier mois saisi (`CAL.ym` doit suivre la dernière séance) ; « oct. »
  + point final donnait « oct.. » ; le 31 octobre 2026 est un samedi (compté avec le vendredi 30) ; une attente de banc
  sur « 50 % » doit accepter l'espace insécable (`\s`).

**v22 — le cycle du compte** (même nuit) : `prop/challenge-option22.html`,
https://claude.ai/artifact/JUcw8gYW2nnVgYMryYKDWx. Blocs MODELE et
TRAVAIL identiques à la v20.
- Événements `EVH` (`alp-option-challenge-ev-v22`, dans la sauvegarde sous `ev`) : `pass` (« J'ai réussi
  l'évaluation », proposé quand l'objectif effectif est atteint : compte financé à zéro) et `pay` (« J'ai demandé un
  retrait », montant proposé = demande possible ; profit − demande, jours qualifiants à 0, `P.ec0` = profit d'après,
  plancher bloqué si `lockPay`). Chaque événement garde l'état d'avant (`s`) et le nombre de journées (`hn`) : annulation
  exacte, repère sur la courbe.
- `P.ec0` nourrit `e0.c0` : les 3 000 suites de l'onglet Compte respectent la règle du cycle en hausse, et « Retrait
  possible » l'exige (avant : `c0` toujours 0).
- Carte « Mes retraits » : part retirée, net contre le prix, liste datée. Courbe réelle : le plus haut repart au changement
  de phase, le plancher bloqué est lu dans chaque journée (`s.elk`), le point d'aujourd'hui suit le profit après retrait.
- `placer(fr)` : placeur d'étiquettes partagé (places candidates, cadre, chevauchements, étiquette facultative).
- **Pièges v22** : une étiquette ancrée à `x ± 6` au bord du cadre a son encadré sur le bord et n'est jamais « libre »
  (prendre ± 9) ; un champ formaté affiche « 1 500 » : un banc compare après avoir retiré les espaces.

**v23 — l'import d'un fichier de trades** (nuit du 8 au 9 novembre) : `prop/challenge-option23.html`,
https://claude.ai/artifact/QdG2pr6JULmaX1zRRD88Tg. Blocs MODELE et
TRAVAIL identiques à la v20 ; nouveau bloc pur **IMPORT** (`lireCSV`, `lireMontant`, `lireDate`, `ordreJM`, `csvSplit`).
- Colonnes reconnues à leur nom normalisé (`CSVCOL` : pnl / profit / P&L…, soldTimestamp / exit time / date…, qty,
  commission) ; séparateur `,` `;` ou tabulation ; montants `$(160.00)`, `1.234,56`, `−5` ; dates ISO, JJ/MM, MM/JJ —
  ordre déduit d'une valeur > 12, sinon mois d'abord si la colonne est un « …timestamp » (Tradovate), jour d'abord
  ailleurs ; un dimanche → lundi (Globex ouvre le dimanche soir), un samedi → vendredi. Sans colonne de frais, la
  commission réglée × quantité est retirée. Aperçu (séances, total, colonnes lues, bouton pour inverser jour / mois),
  puis « Remplacer mon historique » : HIST et EVH vidés, compte à zéro, chaque séance passe par `pushDay` (addDay sans
  rendu, sinon le contrôle contre les réglages se recalculait à chaque séance).
- Carte « Nouveau depuis la v18 » (`#news`, `UI.news` = version) en tête du Résultat, une fois par version.
- Banc : `node tools/challenge-option/controle-import.mjs [page]` (46 contrôles : guillemets, montants, dates, export
  Tradovate, fichier français, colonne de frais, erreurs, 20 000 trades) ; `panneau.mjs` : 9 contrôles de plus.
- **Le format réel de l'export de l'utilisateur n'a jamais été vu** : la lecture est générale, l'aperçu dit quelles
  colonnes ont été prises. Si sa plateforme diffère, demander une ligne d'en-tête et l'ajouter à `CSVCOL`.
- **Piège v23** : `display:flex` sur un `li` qui mêle `<b>` et texte nu fait deux éléments flex — envelopper le texte.

**v24 — finition** (même nuit) : `prop/challenge-option24.html`, https://claude.ai/artifact/8EqQThhxydaC5f6YWUSh7N.
Blocs MODELE, TRAVAIL et IMPORT identiques à la v23.
- « Avant ta séance » (`#plan`, `renderPlan`, appelé en fin de `renderEtat`) en tête de Compte : taille max (k pertes
  d'avance), perte max du jour, plafond du jour (`cons × objectif effectif`) et reste à gagner en évaluation, jour
  qualifiant et retrait en financé ; alerte « plancher proche » sous un quart du drawdown. Prochaine séance : aujourd'hui
  en semaine, lundi le week-end.
- « Copier le résumé » ajoute le compte réel (phase, profit, plancher, marge, chance) et les retraits notés.
- `--dim` passe de #6c6c72 à #7d7d84 : 4,7:1 sur la carte au lieu de 3,9:1 pour tous les textes secondaires.

**v25 — ergonomie et graphiques des captures Marius** (9 novembre 2026, « corrige les erreurs ux ; voici des graphiques,
ajoute-les mais dans la DA de l'app ») : `prop/challenge-option25.html`, https://claude.ai/artifact/2yaHHBf5WJVaFqoTPrQbJZ,
Blocs MODELE, TRAVAIL et IMPORT identiques à la v23.
- **Défauts d'ergonomie corrigés** (relevés sur captures pleine page, compte rempli de 12 séances) : deux grandes cartes
  d'accueil repoussaient le chiffre principal à 1 100 px → une seule carte compacte (`.steps2`, ligne « Nouveau »)
  *après* le héros, bandeau « exemple » juste sous le héros, carte `#news` supprimée ; Compte réordonné (Avant ta séance
  avec le curseur des pertes d'avance → Ma journée → Où tu en es → Tes séances → calendrier → retraits → projections →
  « État du compte » en dernier) ; carte « Taille pour aujourd'hui » supprimée (doublon) ; « Objectif » au lieu du
  « Reste à gagner » en double ; calendrier sans semaines futures ; effacer l'historique vide aussi le calendrier (il
  restait affiché) ; `.qb`, `.ib.sm` 34 px, `.seg.sm` 34 px ; pastille « En évaluation » lisible.
- **Tes séances face à tes réglages** (`#et-ana`, `renderAna`, `anaSim`) : 400 échantillons de n séances tirés avec
  `ST.dayF` (graine fixe, mémoïsés) → éventail P5–P95 / P25–P75 / médiane sous la courbe réelle (ancré à la dernière
  remise à zéro : changement de phase ou retrait, `anaAnchor`), drawdown réel (`#p20`) face au recul médian des réglages
  et au drawdown du challenge, P&L moyen par jour de semaine (`#p21`), tableau réel / réglages (9 lignes + taux de gain
  si les trades sont comptés, point = hors de la bande des 9 sur 10). Rien en mode journal (comparaison circulaire).
- **Quant** : « Combien sur une année ? » (`#p22`, deux panneaux sur le même axe : histogramme des 2 000 années avec
  centiles 5/25/50/75/95, et chance de faire au moins x) ; « Une année, trajectoire par trajectoire » (`P.tj` 2d / 3d) :
  600 années (`trajData`), nuage en mélange additif sur canevas (`drawCloud`) ou relief `Surf3D` en mode traits
  (`D.nobar`, `over24` : rangées de la pire, rose, à la meilleure, verte ; centiles en blanc).
- **Pièges v25** : le placeur jugeait l'encadré (texte + 6 px) contre le cadre — une étiquette ancrée à `x1 − 4`
  n'était jamais libre, et les étiquettes facultatives disparaissaient sans bruit (il juge maintenant le texte) ; une
  étiquette d'axe 3D à gauche ou à droite sortait du canevas (« meilleure ») : `Surf3D` la recale ; `renderJournal`
  sortait avant `renderCal` quand l'historique était vide.

**v26 — plans modifiables, feuille de route, paper** (9 novembre 2026, « personnaliser les data option : la prime, le retrait…,
avec un titre comme MFF Pro Plan qu'on peut modifier ; créer mon paper type SSRN sur ma stratégie ; un espace pour voir le paper
et mon plan de trading en road map interactive ») : `prop/challenge-option26.html`, https://claude.ai/artifact/MRKCjbJH3TUvutYcVmdGeD,
L'utilisateur développe sa stratégie et donnera ses rendements : le paper les attend (champs `TX`, journal, bilan).
- **Le bloc MODELE change** : `demande(R,x,f,q,c0,dc,bd,np)`, pure, partagée par `simCompte` et l'onglet Compte, ajoute tampon
  (`buf`), séances entre deux demandes (`cad`), profit minimal du cycle (`cyc`), meilleur jour du cycle (`fcons`), premier
  plafond (`wmax1`) et montant visé (`cible`) ; sans eux, l'ancienne règle exactement. Option : `morceaux(p)`, `demY`,
  `payoffPts` — avec un tampon la demande est linéaire par morceaux et la valeur s'intègre encore segment par segment ; sans
  tampon, les formules d'origine. « Retrait max » à 0 = sans plafond (le moteur reçoit 10⁹).
- **Plans** (`PL`, `alp-option-challenge-plans-v26`, sauvegarde `pl`) : nom modifiable (`#f-pname`), modèles `TPL` (LucidFlex
  50K, LucidFlex 100K, LucidPro 100K, MFFU Builder 100K, MFFU Pro 100K, Vierge), dupliquer, supprimer en deux touchers ;
  `save()` recopie les règles dans le plan actif. La carte « Mon plan de challenge » remplace « Règles du compte » (ids `b-rg`,
  `sum-rg` gardés) ; l'onglet Option nomme le plan et sa prime et règle le jour du retrait (`#sg-Nopt`). Le compte réel suit le
  plan actif ; ses séances et retraits notés donnent cadence et meilleur jour du cycle (`cycleEtat`).
- **Onglet Stratégie** (`#strategie`, 7e onglet ; barre du téléphone à 9,6 px sous 440 px) : `#sg-sv` route / paper. Feuille de
  route `RT` (`…-route-v26`, sauvegarde `rt`) : six phases, 21 étapes dont 13 vérifiées par les données (`autoEtat` : champs du
  paper, réglages, 20 séances, 30 trades, taux > p0, n50, p < 5 %, espérance, gain du plan, réussite, retraits), cochées seules ;
  la phase en cours seule ouverte (`UI.rop`), mode Modifier (renommer, ajouter, supprimer). Paper (`renderPaper`, `TX`,
  `…-paper-v26`, sauvegarde `tx`) : résumé, JEL, huit sections, jusqu'à six tables et quatre figures SVG écrites à la largeur
  réelle, références, lecture plein écran (`body.reading`), impression (feuille `@media print` blanche), copie du texte ; police
  Source Serif 4.
- **Contrôles** : `node tools/challenge-option/controle-plans.mjs [page]` (35 : ancienne règle sur 2 000 états, plans modèles
  contre le banc indépendant au dollar près, cas écrits à la main, option à tampon contre Simpson) ; `panneau.mjs` + 23 contrôles
  v26 (110 en tout, verts à 390 et 1 280 px) ; `rendu.mjs` lit l'axe italique des fontes ; les 222 autres contrôles et
  `parallele.mjs` passent.
- **Pièges v26** : Playwright refuse de cliquer un bouton `aria-disabled` (étape automatique) — `force: true` ; une barre
  écrasante (70 % de challenges sans retrait) aplatissait l'histogramme du paper — coupée et chiffrée (`clip`) ; « p₀ » sort en
  glyphe de repli en Geist — `p<sub>0</sub>` dans les tables ; un résumé justifié à 390 px ouvre des trous — justifié au-delà de
  640 px seulement ; « l'avantage de ALP-0 » — élision par `de()` ; un renvoi « table n » doit compter les tables réellement
  présentes avant lui (une section vide n'en a pas).

**v27 — journal de trades en R et scellement** (9 novembre 2026, « je vais dev ma stratégie de 0, continue ») :
`prop/challenge-option27.html`, https://claude.ai/artifact/DNtwJgRLDJNXFfybMt1Cpj. L'utilisateur part de zéro et donnera
ses rendements plus tard.
- **Bloc MODELE** : `lireSerie` (série collée : nombres à virgule, « + » gain visé, « - » stop, « = » nul, lettres), `netR`,
  `statsR` (taux, espérance nette, écart-type, t, facteur de profit, pertes d'affilée, recul en R), `fanR` (loi nulle : K suites
  au taux sans avantage, gain wR et perte lR nets, p0 = lR / (wR + lR)). Frais en R d'après les réglages : commission sur chaque
  trade (`cw`), glissement en plus sur un stop (`cl`).
- **Stratégie → Trades** (`#sv-trades`, `P.sv` route / trades / paper) : un toucher par trade (+R visé, −1 R, 0 R) ou une valeur
  libre, série collée, annuler, tout effacer en deux touchers ; six indicateurs et le cumul net en R dans l'éventail de 400 suites
  nulles (depuis le scellement s'il existe). Journal `TL` (`…-trades-v27`, sauvegarde `tl`).
- **Scellement** : fige les réglages (`SK`) et les règles écrites (`SXK`) avec une empreinte SHA-256 (repli FNV-1a) ; les trades
  notés ensuite sont hors échantillon et `bilan()` (journal d'abord, puis Quant, puis séances) ne juge qu'eux ; `sealDrift()` dit
  ce qui a changé depuis ; re-sceller remet le compteur à zéro. Le paper le cite (2.1, 3, 5.1, 7) et ajoute l'annexe A.
- **Feuille de route** : deux étapes automatiques (`seal`, `bt100`), ajoutées aussi aux feuilles gardées (`rtMigrate`, à leur
  place dans leur phase) ; 23 étapes.
- **Contrôles** : `node tools/challenge-option/controle-trades.mjs [page]` (24 : lecture, statistiques à la main, coûts en R =
  tradeStats, loi nulle calibrée — 10 % des suites nulles hors bande à ± 2 points) ; `panneau.mjs` + 15 (125 en tout, verts à
  390 et 1 280 px), ses comptes d'étapes ne sont plus écrits en dur.
- **Pièges v27** : `p.click("summary")` visait « Réglages avancés » — viser `.tl-paste summary` ; `num(v,…,2)` puis `/,?0+$/`
  transforme « 10 » en « 1 » — `rN()` ne retire que les zéros d'après la virgule ; « nº » sortait « no » en Geist — « n° » ;
  l'étiquette « scellée » et celle du cumul se chevauchaient en haut — la première passe en bas du trait.

**v28 — sa stratégie dans le paper** (9 novembre 2026) : `prop/challenge-option28.html`,
https://claude.ai/artifact/4qwzTqhN6ExVQyRpgKuiWt.
- **La stratégie de l'utilisateur, en ses mots** (9 novembre 2026) : « identifier la tendance ; identifier les structures ;
  prendre position sur le début de la structure ; viser loin (max pain) si on a eu un changement de structure donc de
  tendance, ou viser fin de structure et faire du trend following ». Elle est le défaut des champs du paper (`TX0`, sous les
  champs gardés) : tendance (`tend`), structures (`struct`), entrée, invalidation, sortie après changement de structure
  (`sortieA`, max pain), sortie en continuation (`sortie`). **Rien n'est encore défini** : `aPreciser()` liste les sept
  questions (`DEFQ`) tant qu'un champ est vide ou resté à ces mots ; le paper les affiche (encadré « À préciser avant de
  sceller »), le scellement les rappelle, l'étape « regles » de la feuille de route exige les six définitions.
- **Preuve adaptée aux gains variables** : `bootR` (bloc MODELE, bootstrap recentré de l'espérance nette en R, 4 000 tirages,
  p unilatérale et intervalle à 90 %) et `nR` (trades pour une puissance donnée, loi normale). `preuveTL()` choisit le test :
  binomial exact si tous les trades valent +R visé, −1 ou 0, bootstrap sinon ; mémoïsé. Le paper (résumé, 4.2, 5.1, 7, 8,
  référence Efron 1979) et la feuille de route (edge, n50, sig) suivent ce choix.
- **Setups** : deux puces d'un toucher (« Retournement · max pain », « Continuation · suivi ») posent l'étiquette du trade ;
  `parSetup()` donne un tableau par setup (trades, gagnants, espérance, p par bootstrap) dans Trades et en 5.3 du paper.
- **Contrôles** : `controle-trades.mjs` + 8 (32) : taille du bootstrap ≈ 5 % sous une loi asymétrique d'espérance nulle
  (25 % à +3 R), couverture de l'intervalle, puissance à 400 trades, déterminisme, `nR` et preuve dans ≈ 50 % des jeux à
  `nR(…, 0,5)` trades ; `panneau.mjs` + 9 (134 en tout, verts à 390 et 1 280 px).
- **Pièges v28** : attendre plus de 50 % de puissance à 150 trades pour +0,25 R était faux (≈ 41 % en théorie, 31 % mesuré
  avec l'asymétrie) — l'attente d'un contrôle se calcule, elle ne s'estime pas ; un « ? » précédé d'une espace ordinaire passe
  seul à la ligne — espace insécable.

**v29 — le sens de la tendance** (9 novembre 2026, « trader uniquement dans le sens de la tendance aussi ») :
`prop/challenge-option29.html`, https://claude.ai/artifact/Twf6njZR43qpXpuDNxkCTs, **dernière version, c'est elle qu'on
améliore**. Règle ajoutée à la stratégie : **trader uniquement dans le sens de la tendance** ; après un changement de
structure, c'est la tendance nouvelle qui donne le sens. Elle passe dans l'entrée par défaut (`TX0.entree`), la question de la
tendance (`DEFQ.tend`) et le paragraphe du paper qui suit les règles. **Piège corrigé** : la v28 enregistrait tout `TX`,
défauts compris — une sauvegarde gardait l'ancienne formulation par défaut, qui masquait la nouvelle et passait pour une
définition. Désormais seuls les champs écrits s'enregistrent (`txPropre`, stockage et sauvegarde), et une ancienne
formulation par défaut connue (`TXV`) est remplacée à la lecture (`txMaj`). `panneau.mjs` + 3 (137, verts à 390 et 1 280 px).

**Exemples de la stratégie** (trois captures TradingView MNQ1! 1 minute, 9 novembre 2026, heure de New York ; **lecture de
Claude, non encore confirmée par l'utilisateur**) : chute de 27 000 à ~26 760 entre 8 h 30 et 8 h 50, sous l'« IV −1σ »
(26 826) ; retour en V ; vers 9 h 10 le prix reprend le niveau tracé à ~26 888 (dernier plus haut de la baisse) : **changement
de structure**. Puis des longs en escalier, chacun **au retest du plus haut de la structure précédente** : 26 894,50 (stop
26 888,50, 6 pts) → 26 940,50 ; 26 939,50 (stop ~26 931) → ~26 983 ; puis ~27 005, ~27 034, ~27 043, jusqu'aux niveaux
d'options 1DTE (PS 1DTE ~27 05x, CR 1DTE 27 063), où le prix fait un range de 9 h 45 à 10 h 20. Stops de 6 à 10 points,
objectifs de 40 à 46 points (4 à 8 R). Aucun max pain n'est marqué sur les captures. Géométrie 6 / 46 pts : sans avantage
11,5 % de gagnants, seuil frais compris 12,9 % (frais 0,08 R par trade, 0,125 R sur un stop) ; preuve à une chance sur deux en
71 trades si le vrai taux est 20 %, 131 s'il est 18 % ; à 10 / 40 pts le seuil monte à 21,4 %. Les captures montrent des
gagnants choisis après coup : des illustrations, pas des données.

**Comparaison LucidPro 100K / MyFundedFutures Builder 100K** (9 novembre 2026) : règles lues sur les **captures des
tableaux de bord** envoyées par l'utilisateur (les sites ne se résolvent pas depuis le conteneur). Communes : objectif
6 000 $, drawdown 3 000 $ fin de journée, pas de consistance en évaluation, 6 minis / 60 micros, tampon 3 100 $, éval en
un jour. LucidPro : 272 $ (190,40 $ avec coupon), cycle ≥ 750 $ et 3 jours, meilleur jour ≤ 40 % du cycle, limites
journalières 1 800 $ puis 60 % du plus haut de clôture, 90/10 ; retrait 500 $ à 2 500 $ puis 3 000 $ (tiers).
MFFU Builder : **consistance 50 % en financé**, 2 jours par cycle, retrait 1 000 $ à 3 000 $, 80/20, limite journalière
1 750 $, inactivité 7 jours ; prix 282 $ (tiers, non vu sur les captures). `node tools/challenge-option/comparer-100k.mjs
prop/challenge-option25.html` (20 000 challenges, mêmes tirages, 250 séances, 5 retraits au plus) : style régulier
(6 MNQ, 2 trades/j, 45 %, 1,5 R) Lucid +1 480 $ (coupon) / +1 398 $ (prix plein) contre MFFU +1 117 $ ; grosses journées
(1 trade/j, 30 %, 3 R) +1 194 / +1 113 contre +897 ; sans avantage −57 / −139 contre −163. Le 80/20 coûte plus que
l'écart de prix ; le retrait minimum de 500 $ (contre 1 000 $) fait toucher plus de comptes avant leur fin.

**LucidFlex 100K** (9 novembre 2026, captures du tableau de bord) : éval 215 $ (150,50 $ avec coupon, reset 150 $),
objectif 6 000 $, drawdown 3 000 $ fin de journée, limite journalière 1 800 $ ou aucune, retraits à la demande oui / non,
**consistance d'évaluation au choix 40 % ou 50 %**, 6 minis / 60 micros ; financé : drawdown 3 000 $, limite 1 800 $,
aucune consistance, 5 jours par retrait, plan de montée en taille. Tiers : retrait = 50 % du profit, 500 $ à **2 500 $**,
jours qualifiants ≥ 200 $ net, 90/10. Moteur de l'app (6 MNQ, 2 trades/j, 45 %, 1,5 R, 20 000 challenges, prix 150,50 $) :
retirer dès que possible +964 $ par challenge (43 % payés, 1er retrait J95), attendre le plafond de 2 500 $ (profit
≥ 5 000 $) **+1 704 $** (30 % payés, J132) — le retrait précoce bloque le plancher à +100 $ avec 400 $ de marge ;
40 % ou 50 % ne change rien pour ce style régulier.

**MFFU Pro 50K** (9 novembre 2026, sites tiers seulement : le centre d'aide ne se résout pas, le tableau de bord n'a pas été
vu) : drawdown 2 000 $ fin de journée, aucune limite journalière, plancher statique à +100 $ après le 1er retrait, tampon
2 100 $, minimum 1 000 $, **aucun plafond par demande** (100 000 $ cumulés par utilisateur, puis passage en réel), une demande
tous les 14 jours calendaires, 80/20, pas de consistance. Contestés entre sources : retrait unique de 60 % avant d'avoir
franchi le tampon, 90/10, « 2 000 $ par cycle ». `node tools/challenge-option/mffu-pro-50k.mjs prop/challenge-option25.html`
(20 000 comptes financés neufs, 250 séances ; prix de l'évaluation et solde laissé au bout d'un an non comptés) : 4 MNQ
(+30 $/j) tout retirer tous les 14 jours +2 828 $ (retrait médian 1 158 $, 1er J51), attendre 3 000 $ au-dessus du tampon
+2 838 $ (médian 3 132 $, 1er J96) : neutre ; 6 MNQ : attendre 5 000 $ +3 158 $ contre +2 341 $ ; le retrait anticipé de
60 % coûte −777 $ (marge de 600 à 740 $ sous un plancher bloqué) ; loi nulle +559 $.

**MFFU Pro 100K** (9 novembre 2026, page du plan et centre d'aide lus par la recherche, tableau de bord non vu) : objectif
6 000 $, 2 jours au moins, meilleur jour ≤ 50 % **en évaluation seulement** ; drawdown 3 000 $ fin de journée, aucune limite
journalière ; financé : tampon 3 100 $, 1 000 $ au moins, aucun plafond par demande, une demande tous les 14 jours, 80/20,
100 000 $ au total (au-delà perdu), une transaction au moins tous les 7 jours. **Prix non confirmé** : 172 $ chez une revue,
329 $/mois ou 829 $ chez une autre, abonnements mensuels peut-être supprimés le 25 août 2026.
`node tools/challenge-option/comparer-100k-pro.mjs prop/challenge-option25.html` redonne les chiffres de comparer-100k et de
la LucidFlex 100K, puis : style régulier 6 MNQ, Pro à 172 $ +1 181 $ (tout tous les 14 jours) ou +1 521 $ (attendre 3 000 $
au-dessus du tampon), contre LucidPro +1 480, LucidFlex au plafond +1 704, Builder +1 117 ; sans avantage −54 $ ; réussite
55 % en 70 séances (médiane), un challenge sur trois payé ; à 4 MNQ l'ordre s'inverse (attendre +400 $, tous les 14 jours +592 $).

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
