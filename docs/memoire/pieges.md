# Les pièges déjà tombés dedans, et les figures qui se regardent

> Extrait de `CLAUDE.md` (déplacé tel quel, rien n'est réécrit). À lire quand on touche à ce sujet.

## Les pièges déjà tombés dedans

### Le `hash` intégré n'est pas une graine
`robustesse.moments` et `robustesse.queues` amorçaient leur générateur sur
`SEED ^ (hash(loi.cle) & 0xFFFF)`. Le `hash` d'une chaîne est **randomisé par
processus** depuis Python 3.3 : deux exécutions du dépôt tiraient deux jeux de
chiffres différents pour toute la partie XIV, et le README qui promet « deux
exécutions produisent le même document, au bit près » était faux de cette
partie. Rien ne le signalait — les nombres restaient plausibles et les
tolérances des tests les absorbaient — jusqu'à ce qu'un contrôle de borne à
10⁻⁶ tombe d'un côté puis de l'autre sur deux exécutions de la même suite.
`_graine` prend maintenant un CRC de la chaîne. **Toute graine dérivée d'un
nom doit passer par un digest explicite** ; `hash`, `id` et l'ordre d'un `set`
n'en sont pas.

Le test qui l'a trouvé était lui-même mal écrit, et c'est la seconde leçon :
il comparait le minimum d'un échantillon à la borne de la loi avec une
tolérance de 10⁻⁶, donc il dépendait du tirage d'un seul point. Il porte
maintenant deux assertions distinctes — rien ne passe sous le plancher, sans
tolérance aucune ; et le plancher est approché, à 10⁻⁴.

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

### Le chevauchement des fenêtres — trois cents chemins comptés mille fois
Un nœud de faible volume donne onze contacts par demi-séance ; leurs fenêtres
d'une heure se recouvrent presque toutes. Mesurée sur le lot brut, l'excursion
favorable médiane s'écartait de la défavorable d'un bon point — assez pour
qu'on croie lire un effet là où il n'y a que le même chemin recompté.
`setups._independants` applique l'embargo du module `overfit` : dans une
séance, on garde le premier contact puis le premier suivant dont la fenêtre ne
recouvre plus la précédente. **Les fréquences, elles, continuent de se compter
sur le lot entier** — le débit d'occasions n'a rien à voir avec l'indépendance
des observations, et les confondre diviserait le débit par trois.

### La divergence figure/table
Une planche qui coche une case que la mesure aurait refusée est indétectable à
la relecture. La parade est une source unique : `setups.criteres()` rend la
liste des conditions avec leur valeur et leur verdict, `_confirme` n'est que le
« tous » de cette liste, et la figure lit la même liste. Un test l'exige sur
deux cents contacts par niveau.

### Le sommaire figé — trois parties portées par le corps, absentes de la table
Quand la partie XXVII (`ordres.py`) puis la XXVIII (`implicite.py`) puis la
XXIX (`skew.py`) se sont insérées avant la spéculation, le corps du document
a été mis à jour — `<div class="part">`, `<h2 id=…>`, numérotation en toutes
lettres, tout juste — mais le `<nav class="toc">` du gabarit, écrit à la main
dans `docs/prouver-un-jugement.template.html`, ne l'a pas été : il enchaînait
directement de la partie XXVI (volga) sur la spéculation, restée numérotée
XXVII depuis son insertion d'origine, elle-même suivie du protocole en XXVIII.
Rien dans le rendu ne le signalait — la page s'affichait, le sommaire semblait
complet, il omettait simplement vingt-cinq entrées et mentait sur sept autres.
`tests.test_discpaper.TestSommaire` l'a trouvé (`test_ordre_identique`,
`test_les_start_suivent_la_numerotation`), mais seulement quand on l'exécute :
il n'est pas rejoué à chaque reconstruction. La correction est mécanique une
fois vue — insérer les trois `<li>` manquants, recaler `start=` sur le rang
réel (140, 147, 156, 165, 172) — mais rien ne l'aurait signalée sans faire
tourner ce test précis. **Toute insertion de partie doit toucher le gabarit
en trois endroits, jamais deux** : le corps, le sommaire, et si la partie
n'est pas la dernière, la renumérotation en toutes lettres de tout ce qui la
suit.

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

### Une figure doit montrer ce que la section décrit
La planche du flux posait trois bougies d'une minute et trois lignes de
chiffres. Le code était juste, les nombres exacts, et **on n'y voyait ni les
cellules bid × ask, ni le déséquilibre, ni le niveau absorbant, ni le bout
épuisé** — c'est-à-dire rien de ce dont la section parlait. Le défaut ne s'est
pas vu au balayage : aucun débordement, aucun chevauchement, un cadre bien
occupé. Il s'est vu en lisant la légende à côté de la figure.

Deux règles en sortent. Une figure de concept montre **l'objet**, pas son
contexte : le footprint se dessine en cellules, pas en bougies. Et chaque
marque a besoin de son nom dans la figure — un cadre, un liseré, un point ne
disent rien tant qu'une ligne ne dit pas ce qu'ils marquent.

### Le libellé ARIA ne peut porter aucune apostrophe
Il vit dans un attribut, et deux tests l'encadrent par les deux bouts : la
passe typographique de `discpaper` ne visite jamais l'intérieur d'une balise,
donc une apostrophe **droite** y survit et `test_aucune_apostrophe_droite`
la trouve ; une apostrophe **courbe** écrite à la main y est refusée par
`test_les_attributs_sont_epargnes`, qui protège les `href` et les classes.
La seule sortie est de rédiger le libellé sans apostrophe. Idem pour les
pieds de figure et les annotations, qui ne passent pas par `report.inline` :
un `**` **et une apostrophe inverse** y sont publiés tels quels, et deux
tests les refusent. Le second a été trouvé par `test_discpaper` après coup,
sur un pied qui écrivait une formule entre apostrophes inverses ; le test de
module le voit maintenant sans attendre la construction du document.

### Une bande peinte après les barres qu'elle commente
`band_x` pose un `rect.wash` **plein**. Appelée après l'histogramme, elle
recouvre les barres qui tombent dedans : une loi parfaitement unimodale se
lisait comme deux bosses séparées par un creux, et le creux était la bande.
Deux planches de `figrev` en portaient une. Aucun balayage ne le voit — le
code est juste, les nombres exacts, rien ne déborde et rien ne se croise. **Il
s'est vu en regardant la figure.** La règle est d'ordre : tout fond — bande,
aplat, zone — se peint avant ce qu'il souligne, jamais après.

### Une planche qui trace une série sous l'intitulé d'une autre
`figon.fig_on_conditionnel` annonçait « parmi les séances qui cassent » et
traçait la colonne comptée sur *toutes* les séances. Rien ne le signalait :
aucun balayage ne le voit, le code était juste, les nombres exacts, et la
figure montrait un décrochage systématique de cinq points qui n'avait rien à
voir avec son sujet. La parade est celle des setups — la **source unique** —
et son test : lire les infobulles du SVG rendu et les comparer à la mesure.
C'est la seule vérification qui traverse vraiment le rendu.

Corollaire, du même défaut vu de l'autre bout : **une note qui qualifie au
lieu de mesurer finit par mentir**. « La troisième colonne retrouve la
deuxième à quelques dixièmes de point » était faux de trois points aux
courtes distances. Un écart se publie chiffré, et le chiffre se calcule.

### Un texte barré par un tracé ne se voit à aucun balayage
`rect.mjs` croise les boîtes de `text` **entre elles** ; il ne croise jamais
un texte avec un `path`. Une étiquette posée au milieu d'un faisceau de
courbes passe donc les trois balayages et reste illisible. Trois étiquettes
de `figrobu` sont tombées dans ce trou. La parade n'est pas un quatrième
balayage : c'est de ne poser un nom que là où la donnée n'est pas — le ras du
plancher du cadre, la gouttière d'axe (une graduation peut porter un mot :
« 1 × symétrique »), ou la légende sous la planche.

### Une constante fausse qu'aucune relecture n'attrape
`pic_hasard` posait `m* = d²/3σ²`, obtenu en dérivant `u³φ(u)` et en oubliant
que le dénominateur `2Φ(u)−1` dépend lui aussi de `u`. La vraie constante est
la racine de `3/u − u = 2φ(u)/(2Φ(u)−1)`, soit `u* = 1,615` et donc
`d²/2,61σ²` — quinze pour cent d'écart, assez petit pour que les nombres
publiés paraissent plausibles. **C'est un test comparant la forme fermée au
maximum balayé numériquement qui l'a trouvée.** Une forme fermée se contrôle
contre la simulation, sans exception, et le test coûte quatre lignes.

### Une graduation hors domaine ne se voit dans aucun balayage
`Panel.grid_y` et `grid_x` ne découpent pas. Une graduation écrite à la main
au-delà du domaine est tout de même tracée, et elle atterrit **hors du cadre
mais dans la boîte du SVG** — donc invisible au balayage de débordement, qui
ne compare qu'à la boîte du SVG. Deux planches de `figemp` en portaient une,
posée au-dessus de leur en-tête. La parade est un test qui enveloppe les deux
méthodes et refuse toute graduation hors du domaine ; il est dans
`tests/test_emprunts.py` et `tests/test_revue.py`, et il faudrait l'étendre
aux autres modules.

La faute symétrique existe et se voit encore moins. L'échine d'un relief prend
ses graduations d'une liste écrite à la main : `figrev` en avait une plafonnée
à deux cents pour cent sous un sommet à cinq cent cinquante, une autre partant
de zéro quand le sol du relief était à 2,67, et une troisième posant les
décades `0,1 · 1 · 10 · 1 000 · 10 000` — la centaine manquait, et un axe
logarithmique auquel il manque une décade se lit comme un axe dont l'échelle
change en cours de route. Une graduation *hors* du domaine est en plus ramenée
au sol par la projection, où elle se lit comme une valeur du sol : elle ne
manque pas, elle ment. `figrev._echine` déduit maintenant les deux du relief,
au plus quatre graduations — au-delà, la première étiquette d'arête se pose à
la hauteur du coin gauche du sol et l'échine la heurte.

### Un relief à trop grande dynamique ne montre plus rien
La surface du taux de hasard parcourt deux ordres de grandeur : tracée brute,
elle se réduisait à une aiguille au coin des sommets proches, et l'arête que
la section décrit — le lieu `m = d²/u*²σ²` — n'y était **pas visible**. La
légende décrivait donc un fait que la figure ne montrait pas. Rapportée à son
maximum ligne par ligne, la même surface montre exactement ce dont on parle.
Même remède pour la transition de Baik-Ben Arous-Péché : la valeur propre
brute cache le plat, parce que le bord du bruit varie lui aussi avec `γ` ;
`λ − λ₊` pose la région sous le seuil **exactement au sol**.

### Quatre courbes de la même rampe sont quatre courbes indistinguables
Le tracé de Hill en porte quatre. La rampe séquentielle de `figcss` ne les
sépare pas à l'œil au-delà de trois. La parade est le motif de tiret, et
`Board.legend` accepte désormais un troisième champ pour le reproduire —
sans quoi la légende montre quatre traits pleins identiques et ne légende
plus rien.

### Un relief dont la hauteur est une transformée
Deux surfaces de la partie XVII portent un logarithme en hauteur, parce que
leur grandeur parcourt trois ordres et demi de grandeur. `figdisc._surface`
accepte pour cela un `tip_value` : la forme se lit sur la hauteur
transformée, le nombre se lit dans l'unité d'origine, et **l'infobulle ne
publie jamais l'échelle interne**. Sans ce paramètre, un lecteur qui survole
un sommet lisait « 2,73 » là où la grandeur vaut 537 points par heure.

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
