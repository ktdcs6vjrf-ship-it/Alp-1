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

**ALP nº 3** — `docs/prouver-un-jugement.html` (≈1,28 Mo, 52 sections en
quatorze parties, 26 tables, 47 figures dont onze surfaces en nuage de
points). L'évaluation d'un opérateur discrétionnaire dont l'avantage n'est pas
codable, puis **le catalogue des quinze lectures**, puis le seuil de
rentabilité, puis les concepts de sortie, puis la lecture du flux.
Chaîne : `journal.py` → `operator.py` → `attribution.py` →
`report10/11/13/14.py` + `sorties.py` + `concepts.py` + `figdisc.py` +
`figflux.py` + `figsortie.py` + `figcat.py` → `discpaper.py`. Titre courant :
*Le seuil, et non le signal*.

Sa **partie III** est le catalogue : quinze lectures — footprint, carnet, CVD,
VWAP, Fibonacci, profil de volume, profil de marché, gamma, structure de Dow —
rangées par horizon **calculé**, chacune avec sa fréquence sous prix sans
dérive, un exemple tiré d'une séance sans dérive, la réaction du prix ensuite,
et le délai qu'il faudrait pour l'établir. Elle répond à la question d'ordre
que posait le document : le footprint y vient en premier, non par importance
mais parce qu'il est la seule famille prouvable à l'échelle d'une carrière.
Les lois nulles détaillées du flux restent en partie XIII.

Deux autres builds existent — `docs/alp1-paper.html` (`--paper`), version
plus ancienne et plus courte d'ALP nº 1, et `docs/alp2-paper.html`
(`--paper2`), la bande de bruit. Il partage `report*.py` : **une correction
de module s'y propage, donc il faut le rebâtir aussi — et le balayer.** Il a
vécu longtemps hors des trois balayages, et y gardait six chevauchements que
les deux autres documents n'avaient pas.
Dernier artefact : https://claude.ai/code/artifact/c452a408-3263-431f-8b53-373553f12c9b

Derniers artefacts publiés :
- ALP nº 3 : https://claude.ai/code/artifact/4e95dfbc-e717-44e4-ba3e-97102aeafb92
  (précédents : e49bcb16-0228-44f8-bf58-0255216b4d4e, puis
  c360de80-7cdd-4001-a2b7-4a437ce8f0ad)
- ALP nº 1 : https://claude.ai/code/artifact/d6e866f5-1875-4cda-b639-11da99cae35c

L'utilisateur veut **un nouveau lien à chaque amélioration** — publier sous un
nouveau chemin de fichier, jamais republier le même.

## Règles du dépôt — à ne pas enfreindre

1. **Stdlib uniquement.** Pas de numpy, pas de scipy, pas de pandas.
   Python 3.11+. Tout aléa est déterministe et amorcé par une graine explicite.
   (C'est pourquoi `spectrum.py` porte son propre Jacobi.)
2. **Les figures n'écrivent aucune couleur en dur.** Elles passent par les
   jetons CSS de `alp1/figcss.py`. `tests/test_figures_all.py` balaie les douze
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

## Carte des modules

Mesure et géométrie
- `measure.py` — chaîne de mesure, `scan_session`, paramètre `fill`
  (`"stop"` optimiste / `"extreme"` pire cas), `bounds()`.
- `strategy.py` — la stratégie backtestable scellée. Sept portes de confluence
  déclarées, toutes fermées dans `SEALED`. `validate()` : batterie de sept.
- `seuil.py` — `µ* = c/E[τ∧T]`, `Geometry`, `scan`, `best`, `break_even`,
  `friction_grid`, `SURFACE_STOP_PCT`, `PLAUSIBLE_DRIFT_PER_HOUR = (0.6, 3.2)`.
- `horizon.py` / `barriers.py` — temps d'atteinte, probabilités de barrière.
  **`outcome_scaled` : l'exposant de Hurst n'agit que sur `expected_time`.**
  Les probabilités de barrière n'en dépendent pas — c'est le théorème.

Statistique
- `entropy.py` — `required_bits` (Kullback-Leibler), `trades_for_information`,
  Miller–Madow.
- `spectrum.py` — Marchenko-Pastur (`mp_edges`, `mp_density`), transition
  Baik-Ben Arous-Péché (`bbp_threshold = √γ`, `spiked_eigenvalue`),
  `observations_for_spike(s, k) = k/s²`, Jacobi en stdlib.
- `varratio.py` — Lo–MacKinlay. Biaisé à Ĥ = 0,52 sur une vraie martingale.
- `nonlinear.py` — entropie de permutation (Bandt–Pompe), DFA (Peng).
- `overfit.py` — purge, embargo, CSCV/PBO, bootstrap stationnaire.
- `discipline.py` — `k` écarts discrétionnaires valent `2^k` configurations.

Flux d'ordres
- `horloge.py` — le régime de gamma déplace l'horloge, et **seulement** elle.
  À la géométrie déclarée `p(target)` vaut `1/(1+R:R)` à tout exposant, mais
  **c'est conditionnel à ce que la séance ne borne rien** : à stop élargi,
  `p_open` monte à 12 % en chop et la probabilité de touche varie d'un facteur
  35. Quatre tests ont refusé la première version, qui affirmait l'invariance
  sans sa condition. L'inversion : à géométrie fixe, le jour de tendance a la
  **pire** espérance, et le régime ne décide du signe que dans une bande
  étroite de largeurs de stop — sous laquelle la géométrie déclarée tombe.
- `orderflow.py` — LPR, impact de Kyle, CVD, divergences.
- `footprint.py` — déséquilibre diagonal (loi nulle **exacte**, binomiale),
  absorption (`z = Δprix/λ√V`, p-valeur **centrale**), épuisement (loi
  simulée). `CLUMP_DEFAULT = 20` décide de tout, voir ci-dessous.
- `tpo.py` — profil de marché, POC, aire de valeur, tirages simples, extrême
  pauvre, extension de séance — chacun avec sa loi nulle simulée.
- `vprofile.py` — profil de volume, POC, HVN/LVN.

Rendu
- `concepts.py` — **le catalogue des quinze lectures.** `CATALOGUE`, `ordre()`
  (tri par horizon, jamais écrit), `frequence_nulle` (loi du module quand elle
  existe, détecteur simulé sinon), `exigence` (µ* requis, décisions, délai,
  verdict calculé), `reaction` / `eventail` (simulation appariée, exactement
  symétrique sous dérive nulle), `invariant`. **Rien n'y postule l'efficacité
  d'une lecture** — un test l'exige du type lui-même.
- `sorties.py` — **douze concepts de sortie simulés sur trajectoires
  appariées.** Sous prix sans dérive ils rendent tous `−c/a` ; sous dérive ils
  tombent tous sur `(µ·E[τ]−c)/a`. Deux pièges y sont enterrés : l'identité de
  Wald mesure le temps **exposé** (l'intégrale de la taille de position), pas
  le temps écoulé — la prise partielle est la seule règle où les deux diffèrent,
  et sa prédiction échoue tant qu'on prend le mauvais ; et la simulation tourne
  au stop de 0,150 %, parce qu'à 0,6 point une minute de bruit vaut deux fois
  le stop et qu'il n'y a alors *aucun* concept de sortie à discuter.
- `pieds.py` — la prose de pied sort du SVG et se recompose sous la figure.
  **Les quatre documents y passent** ; `paper.py` et `paper2.py` ne le
  faisaient pas, faute de pouvoir importer `workingpaper` sans cycle. Deux règles y sont enterrées :
  une ligne de pied non finale doit finir sur une virgule, sinon le raccord
  la ponctue et coupe la phrase ; et toute phrase qui commence prend sa
  majuscule, sauf si elle ouvre sur une lettre grecque — `µ` capitalisé
  donnerait `Μ`.
- `report*.py` — chacun fournit `values()` et `all_tables()`. `report9` :
  stratégie. `report10` : ALP nº 3. `report11` : le seuil. `report13` : le
  risque refait. `report14` : flux, TPO, information, spectre. `report15` :
  l'audit de l'hypothèse d'edge d'ALP nº 1 — **la colonne de verdict de la
  table `dependance` est calculée, jamais écrite** ; l'ordre des lignes en
  découle, et un test l'exige.
- `fig*.py` — treize modules, chacun expose `render_all()`. `figcat.py` porte
  les bougies, l'éventail des issues et les deux nuages du catalogue. `figterm.py` porte
  `Board`/`Panel`, partagés par `figdisc`, `figflux`, `figpower`, `figquant`,
  `figrisk`. `figures.py` porte `Canvas`, l'ancien moteur d'ALP nº 1.
- `workingpaper.py` / `discpaper.py` / `paper.py` — construisent les
  documents. Toute collision de clé lève une erreur. **Les trois passent par
  `pieds.figure_html`** : c'est ce qui garantit qu'ils traitent une figure
  pareil. `paper.py` ne le faisait pas — il ne pouvait pas importer
  `workingpaper` sans cycle — et gardait sa prose de pied dans ses SVG, où
  elle chevauchait les marques.

Hors du noyau Python
- `pine/alp0.pine` — indicateur TradingView (Pine v6) : VWAP ancré, bandes σ,
  zones d'accumulation, confluence. Barre fermée, sans repeinture.
- `pine/alp0-gex.pine` — report de niveaux gamma. On colle la réponse d'un
  robot Discord ; l'indicateur mesure lui-même la base `NQ − NDX` et la lisse.
  **Ne jamais convertir NDX→NQ à la main : la base saute à chaque roll.**
  Voir `docs/gex-discord-vers-tradingview.md`.
- Ces deux fichiers ne participent ni aux documents ni aux tests : ils n'ont
  pas de loi nulle et n'en revendiquent aucune.

## Les pièges déjà tombés dedans

### La circularité — le pire, et il a survécu longtemps
`quant.reference_drift()` vaut `DRIFT_MULTIPLE × c/E[τ]`, soit **deux fois le
seuil de rentabilité** : la dérive y est dérivée de la friction, donc supposée
exactement au niveau qui rend la stratégie rentable. Elle vaut 16,4 pt/h, soit
5,1 fois la borne haute du domaine que le même document appelle plausible.
Tous les chapitres de risque d'ALP nº 1 en dépendent. `report13.py` les refait
sous une dérive **déclarée** ; ALP nº 3 partie X le documente.

Signe qui trahit la circularité : l'espérance de référence vaut exactement le
ratio de friction. C'est mécanique — si `µ = 2µ*` alors `E[R] = c/L` — et
**le chiffre publié ne dit alors rien du marché, il dit la friction**.

### Le bornage `max(2.0, budget)` — retiré partout, ne pas le remettre
Il fabriquait une taxe de sélection là où il n'y en a aucune, et portait trois
affirmations fausses : un levier à « +0,0000 » quand il porte le seuil de zéro
à 0,0215 ; une géométrie à configuration unique créditée de 1 258 décisions de
taxe ; une surface du mur qui montait dès le premier levier. À une seule
configuration il n'y a rien à sélectionner, donc rien à déflater, et la taxe
vaut **zéro**.

Depuis, les deux routes du mur sont données séparément et c'est leur **maximum**
qui lie. Le fait qui en sort est plus fort : il faut dépasser 22 configurations
pour que la taxe passe devant le test ordinaire, donc **les quatre leviers
recensés ne coûtent rien de plus que ce qu'il faut de toute façon**.

### L'échantillon
Le contrôle d'échantillon doit partir de `REFERENCE_BITS` — l'effet à
*détecter* — et jamais du taux de réussite *observé*, sinon un très mauvais
résultat exige un petit échantillon et passe. Un test verrouille ce point.

### Le paramètre non observable qui décide de la loi nulle
Deux couches en souffrent, et il faut le dire à chaque fois plutôt que de le
cacher :
- **footprint** : la fréquence nulle d'un déséquilibre 3:1 passe de moins d'un
  pour mille à près d'un sur dix selon la taille de grappe (5 → 50 contrats),
  toutes plausibles. Si les contrats arrivaient un à un, ce serait quinze
  écarts-types — le déséquilibre serait un signal parfait, ce qu'il n'est pas.
- **TPO** : la fréquence nulle d'un extrême pauvre passe de 5 % à 37 % entre
  un quart de point et trois points de rangée. Un réglage d'affichage décide
  de la rareté de ce qu'on lit.

### Les surfaces sont des nuages de points, plus des mailles
`figdisc._surface` ne peint plus de mailles pleines : il échantillonne la
surface en quelques centaines de points, dont la teinte et la taille suivent la
hauteur. Deux raisons, et aucune n'est décorative. Une maille pleine **cache ce
qui est derrière elle**, si bien qu'un versant arrière plus haut que le versant
avant disparaissait. Et une maille devait porter un filet couleur papier pour
ne pas se lire comme un aplat, filet qui mangeait la moitié de la surface dès
qu'on raffinait la grille.

Trois repères portent la lecture chiffrée et ne doivent pas disparaître : le
sol en grille de filets, les montants aux quatre coins, l'échine graduée à
gauche. Les sommets de la grille de données gardent chacun leur infobulle.

**Le maximum se met au fond, jamais au premier plan.** En projection
isométrique le coin `(0, 0)` est le plus éloigné ; y placer le maximum fait
monter le relief vers l'horizon, ce qui se lit. À l'ordre inverse, le sommet
tombe au premier plan, où il paraît à la même hauteur d'écran que le coin
lointain — deux points de profondeur différente ne se comparent pas par leur
ordonnée. C'est pour cela que `figcat.HORIZONS` et `figcat.DERIVES` sont
écrits en ordre **décroissant**.

## Les figures se regardent, elles ne se relisent pas

Le code d'une figure peut être juste et la figure fausse. **Tout défaut listé
ici a été trouvé en rendant la page dans un navigateur et en la regardant, et
aucun n'aurait été trouvé en relisant le code.**

### Le domaine écrit à la main — retrouvé huit fois
`Panel.path` découpe au domaine ; les points ne se découpaient pas et se
posaient hors du cadre. Un cadre de `couche_profil` était **entièrement vide**
depuis sa création (domaine 48-86 % pour des valeurs de 90 à 93 %). Le tracé
de `couche_carnet` perdait un morceau au milieu. `figures.Canvas` ne découpait
pas du tout — figures 1, 5 et 6 d'ALP nº 1 dessinaient hors planche. Le
découpage existe maintenant partout, mais **c'est un filet, pas une dispense :
un domaine se déduit des données.** Idem pour `grid_y` et `hline`, qui ne
découpent pas : une graduation écrite à la main hors domaine est tout de même
tracée.

### Une légende écrite devant un cadre borné décrit le bornage — six fois
- « la surface est presque plate le long de l'axe de l'edge » — vrai de la
  fenêtre, faux de la donnée ;
- « les deux faisceaux occupent la même région du plan pendant toute l'année » —
  ils se séparent au trade 240 et leurs lois terminales sont disjointes ;
- « ce que l'exposant décide : la probabilité d'atteindre le target » — **il ne
  la décide pas**, elle vaut 4,76 % à toutes les abscisses, soit exactement
  1/(1+20). Une figure qui affirmait le contraire du théorème d'arrêt
  optionnel, dans le document qui en fait son résultat structurant ;
- une table publiait « la probabilité passe de 3,23 % à 3,23 %, soit une
  division par 1,0 », dans le passage que le document appelle son paramètre le
  plus fragile.

**Élargir une fenêtre oblige à relire sa légende.** Et une colonne constante
sur sept lignes est un signal, pas un détail.

### Les pièges de rendu
- `Panel.area` pose sa classe telle quelle : la feuille ne définit le
  remplissage que sur `.area.ar1`. Passer `"ar1"` seul donne un aplat **noir**.
  Écrire `"area ar1"`.
- `Board.annotation` pose la classe `keep` : sans elle, `extraire_pieds`
  sortait aussi toute prose longue posée près du bas du cadre, et deux
  annotations avaient disparu de leur figure pour reparaître dans la note du
  document.
- `Board.caption` pose `cap`, qui déclare un pied de figure. Sans marque, le
  critère de longueur coupait une phrase en deux.
- `grid_x(dy=)` et `grid_y(dx=)` écartent les intitulés d'axe. Utiles quand
  les graduations sont longues ; à laisser au défaut ailleurs.

### Les trois balayages, à rejouer après toute retouche de figure
Scripts dans le scratchpad de session, une trentaine de lignes chacun, en
Playwright sur le document construit :

1. **débordement et chevauchement** — comparer la boîte *client* (jamais
   `getBBox`, qui ignore les rotations) de chaque `text`/`rect`/`path` à celle
   du `<svg>`, puis croiser les boîtes des `text` entre elles ;
2. **occupation** — pour chaque `rect.frame`, comparer la boîte des marques
   qu'il contient à la sienne. Sous 42 % de la hauteur, relire : c'est ainsi
   qu'ont été trouvés le cadre à 6 % de la grille de Fibonacci et la courbe
   plate de « ce que l'exposant décide » ;
3. en Python, envelopper `Panel.path` et `Panel.dot` pour signaler un tracé
   que le découpage réduit à moins de deux points.

État actuel : **zéro débordement, zéro chevauchement** sur les figures des
**quatre** builds, `docs/alp1-paper.html` et `docs/alp2-paper.html` compris — il ne l'était pas, et
c'est le balayage étendu à ce troisième build qui l'a montré. Le balayage
d'occupation ne laisse que des faux positifs connus (les six cadres de terminal
de la figure 7, les lettres du profil TPO, les niveaux de stop de la figure de
Roll).

## Commandes

```
python main.py --tests      # 935 tests (compter ~25 min, --wp et figures sont lents)
python main.py --wp         # reconstruit docs/temps-de-marche-et-peremption.html
python main.py --paper      # reconstruit docs/alp1-paper.html (version courte)
python main.py --discpaper  # reconstruit docs/prouver-un-jugement.html
python main.py --strategy   # rejoue la stratégie scellée et sa batterie
python main.py --bounds     # la mesure encadrée par les deux remplissages
python main.py --disc       # journal de décision, lois nulles, attribution
```

Modules exécutables directement pour inspecter leurs chiffres :
`python -c "from alp1 import footprint; footprint.main()"` — idem pour `tpo`,
`spectrum`, `seuil`, `report11`, `report14`.

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
