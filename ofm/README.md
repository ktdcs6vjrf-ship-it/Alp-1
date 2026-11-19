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

## Commandes

```
python -m ofm.papier            # reconstruit docs/ofm/la-personne.html (≈ 15 s)
python -m ofm.synthese          # les 59 verdicts, q et budgets, en clair
python -m ofm.<famille>         # demander, offrir, persuader, negocier, choisir,
                                # revenir, calendrier, mesurer : chiffres bruts
python -m ofm.donnees           # rejoue l'extraction (clones bruts requis)
python -m unittest ofm.tests.test_stats ofm.tests.test_ofm   # 26 tests, ≈ 15 s
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

## Vérifier le rendu

Les trois balayages (débordement, chevauchement, occupation) se rejouent en
Playwright sur le document construit, **avec les vraies polices** (récupérées
par `npm install @fontsource/source-serif-4 @fontsource/ibm-plex-mono` et
injectées dans une copie locale) à 360, 390, 768 et 1280 px. État : zéro
partout, aucun défilement horizontal. Puis regarder chaque planche : un
balayage propre ne dit pas qu'une figure montre ce que sa légende affirme.

## Publications

Un nouveau lien à chaque amélioration (copie sous un nouveau nom, jamais la
même URL). Dernier artefact : voir `CLAUDE.md`, section « Hors du corpus — la
série OFM ».
