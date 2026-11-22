# Série OFM — l'avantage humain, cherché comme un signal

Hors du corpus ALP : aucun test du dépôt ne lit ce dossier, et ce dossier ne
modifie aucun module d'`alp1/`. Il en **emprunte** la discipline (loi nulle,
budget d'information, aucun chiffre écrit à la main) et la boîte à outils de
figures (`alp1.figterm`, `alp1.figdisc`, `alp1.figcss`, `alp1.pieds`,
`alp1.discpaper.typographie`). Une retouche de ces modules d'ALP se propage
donc ici : rebâtir et rebalayer.

**Document nº 1** — `docs/ofm/la-personne.html`, *La personne, et non la
phrase* : cinquante-neuf hypothèses sur l'humain qui paie, déclarées d'avance,
testées sur six marchés voisins d'OnlyFans. 16 sections en cinq parties, 23
figures (10 reliefs 3D), 14 tables, deux annexes.

**Version mobile** — `docs/ofm/la-personne-mobile.html` (gabarit
`docs/ofm/la-personne-mobile.template.html`, `python -m ofm.mobile`). Même
source que la version longue — valeurs, verdicts, tables et références viennent
des mêmes modules, les deux versions ne peuvent pas diverger sur un chiffre —
mais une interface de téléphone dans la **direction artistique de l'app Lueur**
(`lueur-ofm/app/globals.css`, couches v16 et v20) : noir `#09090b` et cartes
`#111113`, Inter, un seul bleu électrique `#2e8bff` réservé aux données, tuiles
de stats à grand nombre bleu, encadré « En clair » blanc, barre d'app, puces de
sections, dock du bas, sombre par défaut et clair au bouton. Graphiques dans
`ofm/figmobile.py` : boîte de 340 unités (une unité ≈ un pixel sur téléphone),
la 3D en **blocs isométriques** comme `components/formation/iso.tsx`, une valeur
au toucher sur chaque marque (`data-tip`).

**L'espace « Tous les sujets » (v5).** La page s'ouvre sur un sommaire en tuiles
(`{{SUJETS}}`, construit par `mobile.espace` depuis `GROUPES` et `SUJETS`) et
n'affiche **qu'un sujet à la fois** : 15 sujets de 1 000 à 8 800 px au lieu
d'une page de 59 000 px. Chaque tuile porte la question à laquelle le sujet
répond, sa durée de lecture (mots lus / `MOTS_MINUTE`) et, pour les six marchés,
la barre de ses verdicts — tout calculé. Dans un sujet : retour « Sujets »,
repères qui sautent à l'étude, aux résultats ou à un graphique, barre de lecture,
pied précédent / suivant (`mobile.pied`). Dock : Sujets, Chercher, Suivant (ou
Commencer / Reprendre sur l'espace). La recherche couvre sujets, idées,
graphiques, outils et fiches, sans tenir compte des accents. Ce qui est lu et le
point de reprise restent sur le téléphone (`localStorage`, clés `ofm-cahier-*`).
L'adresse suit la vue (`#demander`, `#chercher`, et `#reprendre` pour le dernier
sujet à l'endroit exact) ; sans JavaScript, la page redevient le long document
précédé de son sommaire. Le titre de l'espace se lit dans la page : l'app Lueur
(`/etudes`, `scripts/etudes/sync.mjs`) sert la même page avec « ‹ Études ».

**Sur ordinateur (v6, 22 nov.)** — au-delà de 1100 px, la colonne de téléphone
(720 px au centre) laissait deux bandes vides. Le sommaire des sujets passe à
gauche, fixe (`<nav class="rail">`, **construit par le script depuis les tuiles
de l'espace** : il vaut pour les deux cahiers sans rien dupliquer en Python), la
lecture prend le reste de l'écran (sections jusqu'à 1 320 px). Le texte garde sa
mesure (62 caractères), les graphiques vont deux par deux, un graphique seul (ou
le troisième d'une suite) pose sa lecture à droite du dessin (sélecteurs `:has`),
les tuiles vont par trois au plus et une rangée incomplète s'élargit au lieu de
laisser un trou, le dock disparaît (le sommaire porte « Tous les sujets » et
« Chercher », touche `/`). Téléphone et page sans script : inchangés.

**Cahier nº 2** — `docs/ofm/cahier-2-mobile.html` (gabarit
`docs/ofm/cahier-2-mobile.template.html`, `python -m ofm.mobile2`), *L'effet,
et non le risque* : 38 hypothèses sur la relance, le ciblage, la fidélité, les
objectifs et la mesure, écrites dans `registre2.py` et **commitées avant le
premier calcul** (l'historique git date la pré-inscription), testées sur cinq
jeux publics (`donnees2.py`, `PROVENANCE2.json`) : Hillstrom (courriel tiré au
sort), Lenta et X5 (SMS tirés au sort), Online Retail II, Kickstarter.
**Sa propre famille BH** (`synthese2.py`) : ajouter ses tests au registre du
nº 1 aurait changé après coup des verdicts publiés. Modules : `relancer`,
`cibler` (Ascarza 2018, hors échantillon), `garder` (BG/NBD revérifié sur un
second marché), `objectif`, puis `figmobile2` (15 graphiques), `clair2`
(textes figés devant `VERDICTS_ECRITS`), `litterature2` (sources et
« Ailleurs »). La page reprend **la feuille, le dock et le script du gabarit
du nº 1** à la construction (`mobile2.commun`), lecture rangée sous
`ofm-cahier2-*`. `cahier-2-valeurs.json` (valeurs, verdicts, hypothèses) et le
champ `verdicts` de `la-personne-valeurs.json` nourrissent le registre des
études de Lueur (`lib/etudes/registre.ts`).

## Commandes

```
python -m ofm.papier            # reconstruit docs/ofm/la-personne.html (≈ 15 s)
python -m ofm.mobile            # reconstruit docs/ofm/la-personne-mobile.html (≈ 15 s)
python -m ofm.synthese          # les 59 verdicts, q et budgets, en clair
python -m ofm.<famille>         # demander, offrir, persuader, negocier, choisir,
                                # revenir, calendrier, mesurer : chiffres bruts
python -m ofm.donnees           # rejoue l'extraction (clones bruts requis)
python -m unittest ofm.tests.test_stats ofm.tests.test_ofm   # 41 tests, ≈ 16 s
python -m ofm.mobile2           # cahier nº 2 et cahier-2-valeurs.json (≈ 75 s : Lenta en bibliothèque standard)
python -m ofm.synthese2         # les 38 verdicts du nº 2
python -m ofm.donnees2 [jeux]   # rejoue l'extraction du nº 2 (bruts dans OFM_BRUT2)
python -m unittest ofm.tests.test_ofm2                         # 27 tests, ≈ 1 min 40
node docs/ofm/parcours-mobile.cjs docs/ofm/cahier-2-mobile.html # même parcours, profil du nº 2
node docs/ofm/parcours-mobile.cjs docs/ofm/la-personne-mobile.html   # 23 gestes vérifiés
INTER=<woff2 Inter> node docs/ofm/balayage-mobile.cjs docs/ofm/la-personne-mobile.html <sortie> 390 360 430 768
```

## Chaîne

`donnees` (extraits + provenance) → un module par famille (`demander` RAOP,
`offrir` Karlan-List, `persuader` Persuasion for Good, `negocier`
CraigslistBargain, `choisir` speed dating, `revenir` CDNOW + BG/NBD/BG/BB,
`calendrier` naissances, `mesurer` étalonnages synthétiques) → `synthese`
(BH sur la famille, verdicts, budgets) → `figures` → `papier`
(gabarit `docs/ofm/la-personne.template.html`).

## Règles

1. **Le registre (`registre.py`) s'écrit avant le calcul.** Changer une
   définition après avoir vu un résultat impose un nouvel identifiant ; les
   deux restent. Les seules retouches d'avant calcul sont racontées dans la
   docstring du registre.
2. **Le verdict est calculé** (`synthese.verdict`) : q de Benjamini-Hochberg
   sur les 59 tests, sens annoncé, signe. Jamais écrit à la main.
3. **Deux paramètres déclarés**, jamais réglés sur ce qu'ils évaluent :
   `TRANSPOSITION = 1/2` et `P_AGENCE = 5 %` (`synthese.py`).
4. **Les données entrent extraites**, sans noms d'utilisateurs, compressées au
   bit près (`mtime=0`), avec leur SHA-256 dans `donnees/PROVENANCE.json`.
   Les clones bruts vivent hors du dépôt (`/home/user/donnees-ext`,
   `/home/user/aseastman/…`) ; `OFM_BRUT` et `OFM_BRUT_RAOP` les déplacent.
5. **Les renvois se calculent** : `{{REF:clé}}` (figure) et `{{REFT:clé}}`
   (table) prennent leur numéro à la construction ; les renvois de section
   sont contrôlés par `test_renvois_de_section`.
6. **Règle de la maison** (skill `ofm`) : aucune tactique qui fasse passer un
   chatteur pour la créatrice, aucun contenu explicite, rien qui vise un fan en
   détresse. La section 14 du document liste ce qui est écarté et pourquoi.

## Les pièges déjà tombés dedans

- **La légende qui affirme au lieu de compter.** « Les points restent dans la
  bande » était faux : 7 sur 55 en sortent (attendu 2,8), et les demandes de
  nuit sont servies à 17,9 % contre 25,2 %. Le pied et le texte publient
  maintenant le compte, et la nuit reste un constat hors registre. Toute
  phrase de pied qui qualifie (« plus du double », « invisible », « des
  centaines ») se remplace par le nombre calculé.
- **Une tactique de conversation n'est pas tirée au sort.** « Merci » et
  « vous êtes libre » suivent un accord ou une hésitation (×1,5) : dans un
  journal de chat, leur signe mesure l'état de l'autre. Même piège pour
  « ferme » en négociation. Ne jamais lire un journal comme une expérience.
- **Le modèle publié peut être faux sur le point qu'il rend célèbre.** BG/NBD
  reproduit au troisième chiffre, et pourtant les fidèles silencieux reviennent
  davantage (R02, seul verdict contraire). Tester la conséquence, pas
  l'ajustement.
- **Le relief qui monte sur son titre.** La hauteur d'une planche en relief se
  calcule depuis `cz`, `cy` et la taille de la grille (`figures._relief`) ;
  les étiquettes d'arête s'éclaircissent selon leur largeur (`_eclaircir`),
  et une probabilité se plafonne à 100 % (`plafond=1.0`).
- **Le champ « heure locale » de RAOP** ne porte que trois décalages (0, +1,
  +8 h) : c'est la machine de collecte. Les heures se lisent à New York.

- **Les mots simples sont écrits devant des verdicts.** `ofm/clair.py` porte,
  pour chaque hypothèse, étude et outil, une explication normale, une version
  « 5 ans » et un exemple ; `VERDICTS_ECRITS` fige les verdicts sous lesquels
  ils ont été écrits, et `TestClair` échoue si l'un change : réécrire le texte,
  jamais le test. Le seul exemple tiré des données (`revenir.exemple_silencieux`)
  est choisi par règle, pas à la main.
- **Un graphique s'explique sous lui-même.** `clair.GRAPHIQUES` porte, pour
  chacun des 24 graphiques mobiles, « ce que tu vois », « ce que ça montre » et
  « pour ton agence » ; un test exige un encadré par graphique. Ces phrases
  décrivent la forme du graphique : si un graphique change d'orientation (le
  relief des fidèles silencieux a été retourné pour mettre le maximum au fond),
  sa phrase change avec lui.
- **Une apostrophe peut se cacher sous une entité.** `html.escape(quote=True)`
  changeait chaque apostrophe des cartes en `&#x27;`, que la passe typographique
  ne voit pas : elles s'affichaient droites dans la v2 publiée. Un nœud de texte
  s'échappe sans les guillemets ; le test cherche aussi `&#x27;` et `&#39;`.
- **Un verdict contraire recopiait le pari réfuté.** La carte de R02 (et la
  colonne « en agence » du classement de la version longue) affichait « le fidèle
  qui se tait est plus perdu » sous le verdict qui établit l'inverse. La phrase
  d'agence passe maintenant par `synthese.en_agence`, qui la retourne en « le pari
  disait… les données disent l'inverse » ; un test le verrouille.
- **L'aperçu mobile sans balise viewport ment.** L'hébergeur d'artefacts ajoute
  `width=device-width` au publish ; un aperçu local qui l'oublie rend une page de
  980 px réduite, et tous les balayages mesurent la mauvaise page. L'injecter.
- **Une étiquette de bloc 3D ne se met pas à l'échelle.** `Scene.rendre` réduit
  l'échelle des blocs jusqu'à ce que blocs *et* étiquettes tiennent, éclaircit les
  étiquettes d'arête selon leur écart à l'écran, et rend la hauteur utile pour que
  la planche ne garde pas de vide sous le relief.
- **La passe typographique courberait le JavaScript.** `mobile._typo` sort chaque
  `<script>` avant `typographie` ; un test compile le script avec `node --check`.
  Les valeurs au toucher vivent dans un attribut : l'apostrophe courbe s'y met à la
  main (`figmobile._bulle`).
- **Un balayage de la page entière ne voit plus que l'espace.** Depuis la v5, un
  sujet fermé est en `display: none` : il n'a plus de boîte, et un balayage global
  rend « zéro défaut » sans avoir rien mesuré. `balayage-mobile.cjs` ouvre chaque
  vue l'une après l'autre.
- **Un attribut lu par le script n'est pas typographié.** Nom et question des
  tuiles (`data-nom`, `data-q`) passent par `mobile._attr` ; sinon la barre du haut
  et la recherche afficheraient l'apostrophe droite et « inconnu? ».
- **`textContent` colle les blocs.** « hasard. » et « Exemple » donnaient
  « hasard.Exemple » dans les extraits de recherche ; le script joint les nœuds de
  texte par un espace (`texte()`).
- **Seul un `#nom` passe entre le lien de l'artefact et la page.** `pushState` ne
  prévient pas l'hébergeur (pas de `hashchange`) : la navigation change
  `location.hash` et ne réagit qu'à `hashchange`. La recherche prend `#chercher`,
  pour que le geste retour la ferme. Dans un test, un `goto` vers la même page avec
  un autre `#` ne recharge pas : passer par `about:blank` pour tester une arrivée.
- **`scrollIntoView` fait aussi défiler la page.** Pour garder le sujet ouvert
  visible dans le sommaire fixe, on règle `rail.scrollTop` à la main ; sinon la
  page sautait à chaque vue.
- **Le saut natif vers `#sujets` cachait le titre de l'espace** sous la barre,
  sur ordinateur (`scrollY` 83 au lieu de 0, depuis la v5). Même parade que pour
  les sujets : `scroll-margin-top: 100vh` sur l'espace.
- **Un défilement doux de 5 000 px dure plus d'une seconde.** Au-delà de deux
  écrans et demi, les repères et la recherche sautent sans animation.

- **Une famille par cahier.** Le BH porte sur un registre déclaré. Ajouter des
  hypothèses à un registre publié change ses valeurs q, donc ses verdicts :
  un nouveau cahier a son registre et sa synthèse.
- **Une campagne à 100 % pile tombait sous l'objectif.** `int((1 − 0,5) /
  0,02)` vaut 24 : le mur de Kickstarter s'affichait dans la tranche 98–100 %.
  Toute tranche se calcule avec une marge (`floor(x + 1e-9)`) et un test le
  vérifie sur des comptes exacts.
- **Un budget « taux » ne s'applique qu'à un taux.** La formule de
  `n_par_bras` compare deux proportions : appliquée à un écart entre deux
  effets (le ciblage) ou à une dépense, elle donnait 0,1 semaine pour
  revérifier ce qui en demande cent fois plus. Ces résultats n'ont plus de
  budget ; la dépense se budgète sur sa variance (`budgets_hillstrom`).
- **Un mur écrase le vide qu'il montre.** 19 082 campagnes contre 26 : en
  échelle linéaire, les tranches sous l'objectif disparaissaient. Échelle
  logarithmique, dite dans la légende et l'encadré.
- **Une étiquette sur un trait barrait une barre** (« aucun : 10,0 % » dans
  le graphique du courriel assorti) : les balayages ne la voient pas ; la
  valeur passe sous l'axe.
- **Un résultat contraire ne devient pas une règle sur un seul marché.** Le
  fidèle silencieux du nº 1 (R02) ne se retrouve pas sur Online Retail II
  (G02 non établi, G03 contraire : le modèle y surestime les silencieux).

## Vérifier le rendu

Les trois balayages (débordement, chevauchement, occupation) se rejouent en
Playwright sur le document construit, **avec les vraies polices** (récupérées
par `npm install @fontsource/source-serif-4 @fontsource/ibm-plex-mono` et
injectées dans une copie locale) à 360, 390, 768 et 1280 px. État : zéro
partout, aucun défilement horizontal. La version mobile se balaie avec Inter
(`@fontsource/inter`) à 360, 390, 430 et 768 px, téléphone émulé et balise
viewport injectée : aucun texte SVG hors cadre ni chevauché, aucun texte de
graphique rendu sous 10,4 px, aucun texte HTML sous 12 px, toutes les cibles
tactiles à 44 px ou plus — **vue par vue** (`docs/ofm/balayage-mobile.cjs`,
16 vues × 4 largeurs). État : zéro partout. Puis le parcours au doigt
(`docs/ofm/parcours-mobile.cjs`, 23 contrôles : tuile, repère, pied, retour,
recherche, reprise, lien direct, page sans JavaScript). Puis regarder chaque
planche : un balayage propre ne dit pas qu'une figure montre ce que sa légende
affirme.

## Publications

Un nouveau lien à chaque amélioration (copie sous un nouveau nom, jamais la
même URL). Dernier artefact : voir `CLAUDE.md`, section « Hors du corpus — la
série OFM ».
