# Desk Recherche & développement — spécification

Contrat du desk « Recherche & développement » d'ALP Desk et de ses études. Il complète
`CONTRACT.md` (API `T.*`, style, vérification) et `LABO.md` (moteur, données) ; lis-les d'abord.

## 0. La demande, et ce qu'on lui doit

L'utilisateur trade le MNQ en intrajournalier, la nuit européenne (00 h – 09 h Paris par défaut),
avec le profil de volume, le footprint, la heatmap du carnet et les niveaux gamma relevés par un
robot (GEXBot) vers 5 h. Il demande, mot pour mot ou presque :

1. **Les zones d'accumulation** : en traçant le profil de volume du début à la fin d'une
   structure, où sont les accumulations, et lesquelles servent de meilleur support ou résistance —
   **et pourquoi**.
2. **Confirmer** au footprint et à la heatmap (absorption, épuisement…).
3. **Ne pas se faire piéger.**
4. **Où mettre l'objectif.**
5. **Les niveaux gamma** : une étude sérieuse pour savoir quand et comment les relever **une
   fois** pour la séance du jour.
6. **Filtrer le bruit** : douze supports et résistances théoriques, et ne pas savoir à
   l'instant t lequel est le bon.
7. **Un manuel** : comment marche chaque concept, à quoi il sert, comment le repérer.
8. Tout comprendre **sans chercher sur internet** : un mode « comme si j'avais 5 ans », un mode
   institutionnel, et un **lexique** qui s'ouvre en touchant le mot ou la phrase.
9. Une **DA améliorée**, et un **desk R&D** qui porte tout cela.

Ce qu'on lui doit, c'est la méthode du dépôt ALP appliquée sans complaisance : **chaque affirmation
est soit vérifiée dans une source citée, soit calculée sur un marché simulé dont on connaît la
vérité, soit présentée comme une hypothèse avec la mesure qui la trancherait.** Aucune donnée de
marché n'est inventée ; aucun taux de réussite n'est annoncé qui n'ait été mesuré. Quand la réponse
honnête est « cela ne se sait pas sans tes données », l'étude le dit, donne le protocole, et le
Labo l'exécute sur ses fichiers.

## 1. Fichiers

| Fichier | Contenu | `T.lib` |
|---|---|---|
| `src/desks/rnd-market.js` | `function rndMarket(a)` autonome : marché simulé à vérité connue + mesures communes | `T.lib.rndMarket` |
| `src/desks/rnd-e0.js` … `rnd-e6.js` | une étude chacune : `function rndStudyEn(a, M)` autonome (M = `rndMarket`) + contenu | `T.lib.rndStudies.en` |
| `src/desks/rnd-lexique.js` | le lexique (≈ 150 termes), deux registres par terme | `T.lib.rndLexique` |
| `src/desks/rnd.js` | le desk : bibliothèque, lecteur, lexique, protocoles ; composants graphiques propres | `T.lib.rnd` |
| `test/rnd-*.test.js` | tests | — |

Ordre alphabétique de `build.py` : `rnd-e0` … `rnd-e6`, `rnd-lexique`, `rnd-market`, `rnd`. Un
fichier d'étude **s'inscrit** au chargement (`T.lib.rndStudies = T.lib.rndStudies || {};
T.lib.rndStudies.e1 = {...}`) mais n'appelle aucune autre bibliothèque avant l'exécution.

## 2. Le marché simulé à vérité connue — `rnd-market.js`

Un carnet d'ordres simplifié, à la tick, inspiré des modèles « à intelligence nulle » (Farmer,
Patelli & Zovko 2005 ; Cont, Stoikov & Talreja 2010 — références vérifiées dans le dossier de
recherche). Chaque séance : 1 380 minutes (Globex), prix sur la grille de 0,25.

**Mécanique de base (loi nulle, `mech: {}`)** : à chaque pas, un ordre au marché arrive (achat ou
vente, probabilité ½, taille tirée) ; il consomme la profondeur affichée au meilleur prix ; quand
elle est épuisée, le prix avance d'un tick. La profondeur se reconstitue par des ordres à cours
limité indépendants de l'histoire, et des annulations. Le prix est une martingale : aucune zone, aucun
signal n'a de pouvoir prédictif, **par construction**. Sorties par minute : OHLC, volume, volume
acheteur (à l'offre) et vendeur (à la demande) **par prix** (le footprint), profondeur affichée des
deux côtés par prix (la heatmap, un instantané par minute), et la vérité terrain (qui a fait quoi).

**Mécanismes plantés**, chacun réglé par une intensité (0 = absent) et documenté par sa source :

- `inventaire` (défenseurs d'accumulation) : pendant une zone d'équilibre, une population prend des
  positions ; quand le prix revient sur la zone, elle la **défend** en ajoutant de la profondeur et
  des ordres au marché contre le mouvement, avec une force qui décroît à chaque test et avec le temps.
  C'est l'hypothèse « les participants défendent leur prix de revient ».
- `liquidite` (liquidité latente) : la profondeur se reconstitue davantage aux prix où beaucoup
  s'est échangé (Kavajecz & Odders-White 2004 : supports et résistances coïncident avec des pics de
  profondeur du carnet).
- `stops` (grappes d'ordres stop) : des stops se regroupent juste au-delà des extrêmes de structure
  et des bords de zone ; déclenchés, ils deviennent des ordres au marché qui prolongent le mouvement
  (Osler 2003, 2005 : cascades d'ordres stop, ordres de prise de bénéfice aux chiffres ronds).
- `spoof` : des ordres affichés de grande taille, retirés avant d'être touchés (mur qui disparaît).
- `iceberg` : des ordres dont seule une partie est affichée, recomplétée après chaque exécution.
- `gamma` : des teneurs couvrent un profil d'intérêt ouvert synthétique ; gamma positif → flux contre
  le mouvement (retour), négatif → flux avec le mouvement (Baltussen, Da, Lammers & Martens 2021).

Chaque mécanisme laisse une **trace mesurable** et une **signature dans le footprint ou la heatmap**
(par exemple, `inventaire` produit de l'absorption au bord de zone). Les études mesurent d'abord la
loi nulle, puis ce qu'on verrait **si** le mécanisme existait, et combien d'occurrences il faudrait
pour l'établir.

**Ops** (`rndMarket({op, …})`, déterministe à graine égale, mulberry32) :
`generate` (séances simulées : colonnes, footprint compact, carnet compact, vérité) ;
`structures` (segmentation en swings : zigzag à seuil k·ATR, au choix du seuil) ;
`profile` (volume par prix sur un intervalle de temps, bins réglables, lissage) ;
`zones` (zones d'accumulation : pics de volume avec proéminence, bords, POC de zone, part du volume,
temps passé, position dans la structure — base, milieu, sommet —, vierge ou testée, âge) ;
`lvn` (creux entre zones) ; `touches` (retours du prix sur une zone : rebond si le prix gagne `e` avant
de perdre `r` au-delà de la zone, cassure sinon, avec **témoin apparié en distance** — une fausse
zone de même largeur placée à la même distance du prix au moment de la formation, partie XIX
d'ALP nº 3) ; `footprint` (déséquilibres diagonaux, empilements, absorption `z = Δprix/λ√V` et
épuisement, portés de `alp1/footprint.py` avec leurs lois nulles) ; `book` (murs, persistance,
retrait avant contact, recomplètement) ; `traps` (balayage puis réintégration, fausse cassure) ;
`gex` (gamma de Black–Scholes, profil par strike, bascule, murs, portés de `alp1/niveaux.py`).

Tests : martingale sous loi nulle (variance des incréments, autocorrélation, aucune zone ne bat son
témoin au-delà de l'erreur d'échantillonnage) ; chaque mécanisme laisse sa trace ; déterminisme ;
autonomie (exécution dans un contexte vide) ; performance (200 séances en moins de 20 s sur la
machine de test).

## 3. Les études

Chaque étude est un **papier de forme SSRN** : titre, série (« Recherche ALP · R&D nº n »), résumé
(institutionnel et « 5 ans »), mots-clés, sommaire, sections numérotées, figures et tables
numérotées, encadrés « À retenir pour ton plan », limites, protocole « Tester sur tes données »,
références vérifiées. Chaque figure a sa **lecture chiffrée** (nombres calculés) et sa phrase « en
simple ». Types de figures variés : lignes, barres, histogrammes, cartes de chaleur, nuages,
éventails, sankey, **surfaces 3D** (au moins deux par étude, maximum au fond), et les composants
propres de la section 4 (profil de volume latéral, footprint, heatmap du carnet, profil gamma).

Le calcul d'une étude : `function rndStudyEn(a, M)` autonome, exécutée dans un worker avec la source
de `rndMarket` ; elle rend `{ results, figures }` (nombres et données des figures). Le texte référence
les nombres par des marques `{{clé|format}}` résolues à l'affichage : **aucun nombre de résultat n'est
écrit à la main** (règle du dépôt). Un test vérifie que toute marque du texte existe dans `results`.

- **R&D nº 0 — Le manuel.** Chaque concept, dans l'ordre où l'opérateur le rencontre : enchère et
  équilibre, profil de volume (POC, zone de valeur, HVN, LVN), profil de marché (TPO), VWAP et bandes,
  structure (swing, impulsion, range), zone d'accumulation, footprint (bid × ask, delta, CVD,
  déséquilibre, empilement, absorption, épuisement), heatmap du carnet (profondeur, mur, retrait,
  iceberg, spoofing), balayage et piège, objectif et portée de séance, gamma (GEX, bascule, murs,
  0DTE), bruit et multiplicité. Pour chacun : **ce que c'est, le mécanisme, à quoi ça sert, comment le
  repérer, sa fréquence sous loi nulle quand elle se calcule, ses pièges**, une figure tirée du marché
  simulé, et sa version « 5 ans ».
- **R&D nº 1 — Les zones d'accumulation.** Profil de volume du début à la fin d'une structure ; où
  sont les zones ; lesquelles tiennent et pourquoi. Hypothèses classées, chacune avec son mécanisme et
  sa prédiction mesurable : fraîcheur (zone vierge), taille (part du volume, temps), position (la base
  d'où part l'impulsion), bord contre cœur (bord de zone contre POC), confluence (VWAP, niveau gamma),
  nombre de tests. Résultats : sous loi nulle, aucune ne bat le témoin (avec l'erreur d'échantillonnage
  publiée) ; sous `inventaire` et `liquidite`, lesquelles ressortent, de combien, et **combien de
  retours il faut** pour l'établir (puissance). Surfaces : taux de rebond en fonction de (part du
  volume, nombre de tests), écart au témoin en fonction de (fraîcheur, distance). Conséquences pour le
  plan : où se place le stop (au-delà de la **largeur** de la zone), quelles zones garder.
- **R&D nº 2 — Confirmer au footprint et à la heatmap.** Chaque signal, sa fréquence sous loi nulle (le
  déséquilibre 3:1 dépend de la taille de grappe : partie XIII d'ALP nº 3), son taux de rebond
  conditionnel à une zone ; sous loi nulle la confirmation **divise l'échantillon sans déplacer
  l'espérance** (ALP nº 3, grammaire du setup : 49,4 % contre 50,1 %) ; sous `inventaire`, l'absorption
  au bord de zone devient informative — de combien, à quel coût en occasions perdues. Heatmap : ce
  que `spoof` fait au signal « mur », ce que `iceberg` fait à « profondeur affichée ». Ce qui confirme
  quoi, et ce qui ne confirme rien.
- **R&D nº 3 — Les pièges.** Balayage puis réintégration, fausse cassure, piégés de la cassure.
  Fréquence sous loi nulle (une marche dépasse un extrême puis revient : c'est l'arcsinus et la
  réflexion), fréquence sous `stops` (Osler), ce qui distingue un balayage d'une vraie cassure **au
  moment où l'on doit décider**, et la géométrie qui protège : entrée après réintégration, stop au-delà
  de l'extrême du balayage plus la largeur de zone, invalidation au temps. Sous loi nulle, toute règle
  rend `−c/L` : la protection est une question de géométrie et de coût, pas de lecture.
- **R&D nº 4 — Où placer l'objectif.** Arrêt optionnel (`P(objectif) = a/(a+b)` sans dérive, espérance
  indépendante de l'objectif) ; portée de séance (ALP nº 3, partie XXX : un objectif hors de portée
  rend sa probabilité nulle) ; sous `inventaire`, l'objectif placé avant la prochaine zone opposée
  contre au-delà ; sorties partielles et suiveur (ALP : tous rendent `−c/L` sans dérive). Surfaces :
  espérance en fonction de (distance de l'objectif, distance de la zone opposée).
- **R&D nº 5 — Les niveaux gamma : quand les relever.** Ce qui fait bouger un niveau : l'intérêt
  ouvert (publié une fois par jour — à citer depuis le dossier vérifié), le prix de référence, la
  volatilité implicite, le temps restant ; pendant la nuit européenne, lesquels de ces intrants
  bougent réellement (à établir par le dossier de recherche : heures de cotation des options sur
  Nasdaq-100, mise à jour de l'indice) ; déplacement calculé de chaque niveau (murs de strike,
  bascule, gamma maximal) entre 00 h, 05 h, 08 h 30 et l'ouverture, en points et en multiples du stop ;
  largeur d'un niveau (`√(2 ln 2)·σ√T`, partie XIX). Réponse : quels niveaux sont stables sur la
  séance, lesquels ne le sont pas, quand un relevé unique suffit, comment convertir l'échelle (base
  `NQ − NDX`, `pine/alp0-gex.pine`), et le protocole pour vérifier sur ses propres relevés.
- **R&D nº 6 — Filtrer le bruit.** Avec k niveaux, la probabilité qu'un prix soit « sur un niveau » par
  hasard ; pourquoi le bon niveau ne se connaît qu'après ; le rapport de vraisemblance de chaque
  confirmation (1 sous loi nulle) ; un **plan de tri déclaré d'avance** : au plus trois niveaux par
  séance choisis par un classement écrit avant l'ouverture, une confirmation par niveau, une
  invalidation, et ce que ce filtre coûte en occasions et en délai de preuve. Un arbre de décision
  imprimable pour la séance.

Chaque étude a un **protocole « Tester sur tes données »** : une stratégie du Labo (gabarit écrit dans
`labo/strategies` par le bouton) ou une mesure de l'étude rejouée sur un jeu de l'utilisateur
(`T.lib.donnees.loadDataset`) — barres seulement pour nº 1, 3, 4, 6 (profil de volume approché à
partir des barres, déclaré tel) ; le footprint réel (nº 2) exige un export par prix et sens que l'étude
décrit.

## 4. Le desk — `rnd.js`

`id: 'rnd'`, `label: 'Recherche & développement'`, `glyph: '§'`, `group: 'Recherche'`, `order: 47`.
Onglets : `bibliotheque`, `lire`, `lexique`, `protocoles`.

- **Bibliothèque** : une carte par étude (numéro, titre, résumé court, temps de lecture, nombre de
  figures, état du calcul) ; « Lire ».
- **Lire** : le papier. En-tête de forme SSRN ; **interrupteur de registre** « Institutionnel /
  Comme si j'avais 5 ans » (persisté) qui change chaque paragraphe pour sa version simple, les nombres
  restant identiques ; sommaire repliable ; figures numérotées ; encadrés « À retenir » ; références ;
  calcul dans un worker avec progression, résultats mis en cache (mémoire, et `T.store` si la taille le
  permet).
- **Lexique** : tous les termes A–Z, recherche, filtre par étude ; chaque fiche a la définition
  institutionnelle, la version simple, la formule s'il y en a une, les termes liés (touchables), et les
  études où le mot apparaît.
- **Protocoles** : la liste des tests à faire sur ses données, avec le bouton qui crée la stratégie du
  Labo ou lance la mesure.

**Lexique cliquable.** Dans tout texte d'étude, `[[terme]]` ou `[[texte affiché|id]]` devient un mot
souligné en pointillé violet ; le toucher ouvre une **feuille du bas** (bas d'écran sur mobile, carte
flottante au-delà de 760 px) avec la fiche du terme, deux registres, les liens. Un test refuse toute
marque dont l'identifiant n'existe pas dans `T.lib.rndLexique`, et tout terme du lexique sans les deux
registres. `**gras**` et `*italique*` sont permis ; rien d'autre (pas de HTML dans le contenu).

**Composants propres** (canvas, à la largeur réelle, info-bulle au toucher, jetons CSS seulement) :
`vpChart` (prix dans le temps + profil de volume latéral, zones ombrées, POC, bords, témoins),
`footprintChart` (barres × prix, nombres bid × ask, déséquilibres surlignés, POC par barre),
`bookHeatmap` (temps × prix, intensité de la profondeur, trace du prix, exécutions), `gexProfile`
(GEX par strike, bascule, murs, prix). Surfaces 3D : `T.lib.perf.charts.surface3d` (`injectCss()`
avant).

## 5. DA

Le lecteur suit la direction artistique du document nº 3 du dépôt (voir `CLAUDE.md`, « La direction
artistique du document nº 3 ») : **un seul accent**, le violet des planches, pour les numéros de
section, de figure et de table ; un lever de section est une respiration (filet court en accent),
pas un titre plus gros ; corps en Geist 16 px, interligne 1,65, colonne de 68 caractères ; titres en
Instrument Serif ; au-delà de 1 024 px, le numéro de section descend dans la marge. Les figures ont
leur numéro dans la teinte de leur courbe principale. Le mode « 5 ans » se signale par un liseré
discret, pas par une autre police.

Pour l'application entière : un passage de polissage après l'intégration du Labo et du desk R&D —
hiérarchie typographique, rythme vertical, cartes et indicateurs plus nets, états vides soignés,
graphiques homogènes (mêmes marges, mêmes graduations, mêmes info-bulles) — sans changer une
couleur hors des jetons, et sans un seul défaut au banc de rendu.

## 6. Tests et vérification

Par fichier : `node test/rnd-<nom>.test.js`. Obligatoires : autonomie et déterminisme de
`rndMarket` et de chaque `rndStudyEn` ; martingale sous loi nulle ; trace de chaque mécanisme ;
**aucune zone, aucun signal ne bat son témoin sous loi nulle** au-delà de deux erreurs-types ; chaque
marque `{{…}}` du texte existe dans les résultats ; chaque `[[…]]` existe dans le lexique ; chaque terme
a ses deux registres ; aucune phrase avec `undefined`, `NaN` ou vide ; temps de calcul de chaque étude
≤ 15 s sur la machine de test. Puis construction complète, banc `test/e2e.js` → `"bad": 0` à 390 et
1 280 px, et **regarder les captures** de chaque étude dans les deux registres, avec une fiche du
lexique ouverte.
