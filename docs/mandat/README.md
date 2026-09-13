# Mandat NQ — le document de reporting privé

Ce dossier porte un objet qui ne ressemble à rien d'autre dans le dépôt : un
**fichier HTML autonome**, sans construction, sans dépendance, sans test de
structure. Il est publié en artefact Claude et envoyé à un bailleur privé.

`mandat-nq.html` — un seul fichier : un `<style>` en ligne, un `<script>` en
ligne. Aucune bibliothèque. Les treize planches sont des SVG écrits à la main
par `document.createElementNS`, construits au chargement.

## Ce qu'il faut savoir avant d'y toucher

1. **Un nouveau lien à chaque édition.** On ne republie jamais la même URL :
   on copie le fichier sous un nouveau nom et on publie ce nouveau chemin.
   C'est délibéré — le destinataire est certain d'ouvrir la dernière version.
2. **Noir et blanc strict.** Aucune teinte, nulle part. Une distinction
   catégorielle passe par la valeur (blanc contre gris) ou par le motif de
   tiret, jamais par la couleur.
3. **Aucun défilement horizontal, à aucune largeur.** Vérifié à 360, 390,
   430, 768 et 1100 px. Les planches se redimensionnent, elles ne défilent pas.
4. **`ETROIT` décide de tout.** Le drapeau vaut `window.innerWidth < 760` et
   il est calculé une seule fois. Sous ce seuil les planches passent d'une
   boîte de 1000 à une boîte de 430, et la typographie retrouve sa taille
   réelle. Une planche de 1000 rendue dans 390 px tombe à 0,39 d'échelle :
   un intitulé de 14 px y vaut 5,5 px, c'est-à-dire rien.
5. **L'aléa est déterministe.** `rng(seed)` est un mulberry32 ; les bougies
   passent par une MA(1) à coefficient négatif (rebond bid-ask). Deux
   ouvertures de la page donnent le même document.
6. **Les chiffres de la prose sont lus dans le code.** La géométrie déclarée
   en section 03 (stops, rapport, friction, séances) est posée au chargement
   depuis `OUTILS`, `FRICTION` et `SEANCES_MOIS` : la prose ne peut pas
   diverger de la planche 5.1.

## Les pièges déjà tombés dedans

Tous ont été trouvés **en regardant la page**, aucun en relisant le code.

- **Une étiquette de prix tronque la graduation sous elle.** `tag()` retire
  désormais la graduation qu'elle recouvre, comme une vraie échelle de prix.
- **Une fenêtre posée sur les barres qu'elle commente.** L'encart des
  percentiles de la figure 5.2 en cachait une dizaine. Les barres montent à
  80 % du cadre et la bande du haut est libre par construction.
- **Un axe tracé dans le nuage.** L'axe des séances de la figure 5.3 était
  barré par les trois percentiles. Il vit dans une gouttière sous la planche.
- **Un texte croisé par un tracé ne se voit à aucun balayage.** Parade :
  `text.halo` (`paint-order: stroke`), un liséré noir, comme sur une
  plateforme de cotation. Appliqué aux niveaux, aux Fibonacci, aux VAH/POC/VAL.
- **Une étiquette entre dans la gouttière des prix.** `pill()` prend un
  `maxR` et se décale plutôt que de déborder.
- **Une prose de pied ancrée à droite sort par le bord gauche.** Le pied de
  la 5.1 tenait sur deux colonnes dont la gauche débordait de la planche.
- **Un trait tiret-point de vingt pixels se lit comme un point
  d'exclamation.** Un repère court se trace plein.
- **Le sommaire ne suit pas l'insertion d'une section.** Toute section
  insérée touche le corps, le sommaire et la renumérotation de ce qui suit —
  trois endroits, jamais deux.

## Vérifier

Les fontes réelles sont récupérées par npm (`@fontsource/ibm-plex-mono`,
`@fontsource/source-serif-4`) et injectées dans un aperçu local : sans elles
la relecture visuelle se fait dans une police de repli, plus large, et la
moitié des défauts ci-dessus reste invisible.

```
python3 mkpreview.py       # aperçu local avec les vraies fontes
node errs.mjs              # erreurs de script et planches vides, six largeurs
node audit.mjs             # débordements, chevauchements, occupation
node scrollcheck.mjs       # aucun défilement horizontal, cinq largeurs
node valid.mjs             # hauteurs de blocs — attrape une balise non fermée
node printtest.mjs         # export PDF et rendu en média impression
node mfig.mjs f-mc f-gex   # une planche au format téléphone
node figshot.mjs f-mc      # une planche au format large
```

Les scripts attendent `preview_s38.html` dans le dossier courant et Chromium
à `/opt/pw-browsers/chromium`. **Ne jamais lancer `playwright install`.**
