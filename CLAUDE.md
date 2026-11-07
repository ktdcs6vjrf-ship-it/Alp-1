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
