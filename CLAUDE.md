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

**ALP nº 3** — `docs/prouver-un-jugement.html` (136 sections en vingt-six
parties, 140 tables, 199 figures dont cinquante-huit surfaces en nuage de
points). L'évaluation d'un opérateur discrétionnaire dont l'avantage n'est pas
codable, puis **le catalogue des quinze lectures**, puis **la grammaire du
setup**, puis le seuil de rentabilité, puis les concepts de sortie, puis la
lecture du flux. Chaîne : `journal.py` → `operator.py` → `attribution.py` →
`report10/11/13/14.py` + `sorties.py` + `concepts.py` + `setups.py` +
`figdisc.py` + `figflux.py` + `figsortie.py` + `figcat.py` + `figsetup.py` +
`robustesse.py` + `figrobu.py` + `overnight.py` + `figon.py` +
`emprunts.py` + `figemp.py` + `fonds.py` + `figfds.py` + `revue.py` +
`figrev.py` + `niveaux.py` + `fignv.py` + `grandeurs.py` + `figgra.py` +
`theta.py` + `figth.py` + `vega.py` + `figvg.py` + `rho.py` + `figrh.py` + `vanna.py` +
`figva.py` + `charm.py` + `figch.py` → `discpaper.py`. Titre courant : *Le seuil, et non le signal*.

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
- ALP nº 3 : https://claude.ai/code/artifact/9131a050-4cb4-471a-96f1-186be73aceb4
  (précédents : 6aa40bf9, 340834bd, 5a666d3a, 9e0ef040, 8edc727c, b40a2d6b,
  e5f06e51, 614afa35, 213dccda, a990ef0e, c2cbc5ee, d1e5eca9, 82bd1a42,
  601106cf, dcb59260, d5e2c22b, 99a53614, f9f5d005, 4e95dfbc, e49bcb16,
  c360de80)
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

Sa **partie XIV** répond à l'objection de la loi normale — `robustesse.py` +
`figrobu.py`. Six lois d'incrément à variance identique, dont une Student à
trois degrés (moment d'ordre quatre divergent), une loi à sauts négatifs
compensés (l'asymétrie réelle d'un indice, **négative**), et une loi
exponentielle recentrée qui prend au mot « la baisse est plafonnée, la hausse
est illimitée ». Résultat : *les six rendent `−c/a`*. Ce que les queues
déplacent, c'est le temps de marché, donc le seuil — et la géométrie le
déplace **7,5 fois plus** que la forme des queues. Deux pièges y sont
enterrés : l'appariement antithétique est interdit sur une loi asymétrique
(nier un incrément change sa loi), et le seuil de verdict est corrigé de
Bonferroni sur les douze verdicts de la campagne, faute de quoi une ligne
portait « réfutée » sur un faux positif attendu 46 % du temps.

Sa **partie XV** applique le protocole à une affirmation venue **du dehors** —
`overnight.py` + `figon.py`. Sept nombres publiés sur les extrêmes de la
session 18:00–09:30 du NQ, dont le fameux « ouverture au-dessus du milieu →
le haut casse en premier 76,2 % ». Le mécanisme tient en une phrase :
l'ouverture de 9:30 **est** le dernier point de la session overnight, et le
point terminal d'une marche tombe près d'un bord de son propre range (loi de
l'arc sinus) — distance médiane **20,9 %** contre 79,1 % à l'autre bord. La loi
d'arrêt rend alors le 76 % sans qu'aucune donnée de marché n'entre.

Trois pièges y sont enterrés. Le modèle nul a deux paramètres non observables,
**calibrés sur les deux nombres sans direction** (les deux côtés cassés, aucun
cassé) pour qu'il ne reste aucun degré de liberté sur les nombres de direction.
Une hypothèse séduisante — la dispersion de volatilité comblerait le résidu —
est **réfutée par la mesure et publiée comme telle**. Et le verdict bascule sur
un **dénominateur que la publication n'écrit pas** : selon que les 76 % portent
sur toutes les séances ou sur les seules qui cassent, l'espérance vaut +0,0439
ou −0,0202 R. Le taux d'équilibre de cette géométrie vaut **77,4 %**.

Sa **partie XVI** emprunte cinq disciplines constituées et publie, pour
chacune, la fréquence de son motif sous prix sans dérive — `emprunts.py` +
`figemp.py`. L'ordre est celui de ce qu'elles touchent dans
`E[R] = (µ·E[τ∧T] − c)/a`. ① **L'unité d'observation** : le nombre d'années
requis pour établir un Sharpe ne dépend **pas** du pas de temps observé — la
colonne est constante et c'est le résultat — et la multiplicité ne coûte que
le logarithme du nombre de candidats (4,66 pour 262 144 configurations).
② **L'analyse de survie** : taux de hasard d'un extrême, censure à droite par
la sortie de l'opérateur, Kaplan-Meier, loi nulle **fermée** par le principe
de réflexion, courbe de calibration. ③ **Hawkes** : noyau d'Omori, ratio de
branchement 0,75, rapport de Fano contre sa bande de Poisson, intensité de
Palm. ④ **Valeurs extrêmes** : loi de l'arc sinus pour l'heure du haut, GPD et
tracé de Hill. ⑤ **La détection** : `d′` et le critère, la seule des cinq qui
touche `µ`. Verdict calculé : **quatre déplacent l'horloge ou le risque, une
seule le sens.**

Sa **partie XVII** part d'un objet extérieur : les trois nombres publics d'un
fonds quantitatif qui n'embauche aucun opérateur — `fonds.py` + `figfds.py`.
Elle ne conteste rien ; elle demande ce que ces nombres exigent. La loi
fondamentale `IR = IC·√N` répond, et à l'envers de ce qu'on en dit d'habitude :
le nombre d'années requis pour établir un ratio ne dépend **pas** de `N`
(1,55 an par la route de l'information, 1,96 par celle du Sharpe, et aucune
des deux ne bouge avec `N`) — ce que l'ampleur achète est la **petitesse de
l'exigence**, qui tombe de 4,45 points de taux à 0,06. Le seuil de crédibilité
se calcule : **9,9 décisions par séance**, au-dessous desquelles revendiquer
un ratio de 2 revient à revendiquer un avantage que personne n'aurait
remarqué. Le taux publié de 50,75 % demande 27 477 décisions pour être
distingué du hasard — 55 ans pour un opérateur, 4 jours pour une
infrastructure.

Puis le retournement, en trois pratiques que l'opérateur seul possède. Le
**panier de lectures** sature : à corrélation 0,15, quinze lectures valent
2,20 fois une seule et non 3,87 — le plafond est `1/√ρ`, fixé par la
corrélation et jamais par le nombre. La **capacité** est le seul axe où le
petit est structurellement en avance : l'impact croît en `√Q`, il pèse 13 %
de la friction à un contrat et la capacité de la géométrie vaut 888 contrats.
L'**exécution** divise `µ*` par 2,22 en changeant l'entrée seule — plus que
tout ce que le document obtient en changeant de signal — et la dérive adverse
qui reprendrait ce gain vaut 0,45 pt/h, **au-dessous du plancher plausible**,
donc invisible sans un protocole écrit d'avance. Verdict calculé : quatre des
cinq pratiques transfèrent, aucune ne touche à la direction.

Sa **partie XVIII** applique le protocole à deux résumés de performance venus
du dehors — `revue.py` + `figrev.py`. Aucune donnée, aucun code : rien que les
nombres publiés. Quatre questions, et elles se posent à n'importe quelle note.
① **La redondance interne** : les métriques d'un résumé se déduisent les unes
des autres, et sept recalculs se referment. Le plus instructif ne coûte rien à
personne — le rapport Sortino sur Sharpe tombe à 0,1 % de `√2`, la valeur
exacte d'une loi **symétrique**, donc *le Sortino publié n'ajoute rien au
Sharpe publié* ; et inverser l'alpha de Jensen sort du document un rendement
de marché que personne n'a besoin du document pour vérifier. ② **La bande du
Calmar** : son dénominateur est un maximum, et il n'y a qu'un seul maximum
dans une série quelle que soit sa longueur. Sous la loi la plus favorable qui
soit — rendements indépendants et gaussiens, donc une **borne inférieure** de
l'incertitude — la bande à 90 % mesure 139 % de sa médiane, et l'amélioration
de 0,22 point que le document revendique en occupe 26 %. Elle demanderait 61
ans pour sortir du bruit. ③ **La corrélation de Pearson ne voit pas ce qui
compte** : un krach commun de huit écarts-types tous les dix ans n'induit que
ρ = 0,025, quand 4 964 séances n'établissent que |ρ| ≥ 0,040 — la limite de
visibilité est à un krach partagé tous les 6,1 ans. Sur le maximum de perte,
cette dépendance coûte quelques points ; sur la **pire séance**, un facteur
2,98. *La diversification protège toutes les séances sauf celle qui compte.*
④ **Ce qui n'est pas publié décide** : deux Calmar contraignent la réduction
de maximum et le budget de prime à un lieu d'une dimension, que la partie
parcourt ; et la capacité d'une stratégie intraday décroît comme le **carré**
de la rotation, jusqu'à s'annuler au-delà de 45 aller-retours par séance, un
nombre qu'aucun des deux documents n'écrit. Verdict calculé : les cinq
lectures se récupèrent sans les données, et **aucune ne donne un avantage
négociable** — ce qui se récupère est une méthode de lecture, jamais une
direction.

Deux pièges y sont enterrés. Un ajustement postulé — la demi-largeur de la
bande décroît « en racine de l'horizon, la vitesse de toute moyenne » — est
**réfuté par la mesure** : l'exposant vaut 0,61, et la racine manque les
points simulés de 19 %. L'exposant est donc ajusté, coefficient et puissance,
et un test refuse le demi. Et le balayage d'horizons tenait dix minutes avant
qu'on remarque que le maximum de perte des `T` premières années est une
statistique de **préfixe** : une seule simulation à l'horizon le plus long,
relue à ses jalons, rend exactement le même résultat en vingt secondes — et
aligne les colonnes sur le même aléa, ce qu'on voulait voir de toute façon.

Sa **partie XIX** part d'un guide d'options extérieur consacré au gamma des
teneurs — `niveaux.py` + `fignv.py`. Le guide fait ce que la vulgarisation ne
fait jamais : il publie le résultat de son propre test, mesuré **contre un
niveau témoin placé à la même distance de l'ouverture**, et il ne trouve rien.
Le dépôt reprend ce contrôle, qui lui **manquait**, et en tire quatre choses.

① **Le témoin apparié en distance.** Le taux de touche est celui du principe
de réflexion et ne dit que la distance ; le taux de réussite d'un trade pris
sur le niveau vaut `1/(1+R:R)` — **constant à toute distance**. D'où l'identité
de la partie : l'excès requis vaut `δ = (c/a)/(1+R:R)` et l'échantillon
`n = z²·(R:R)·(a/c)²`. *L'exigence décroît comme la friction relative et la
preuve croît comme son carré* — le budget d'information de la partie IV,
retrouvé par une route entièrement différente, et les deux s'accordent à 9 %
(519 contre 474). Un piège y est enterré : `a/(a+b)` est le taux du problème
**non borné**, et la table publie `p_open` en colonne parce qu'aux stops
larges la séance borne et que les deux dernières lignes ne sont plus qu'un
ordre de grandeur.
② **La définition fabrique le taux.** « Tenir » se définit par deux distances,
et l'arrêt optionnel rend `e/(r+e)`. Un recul d'un tick avant une extension de
quatre points rend **94 %** de tenue sur du bruit pur : *c'est pour cela que
tout niveau publié « fonctionne »*.
③ **Un niveau a une largeur.** Celle du gamma vaut `√(2 ln 2)·σ√T` = 1,177 σ√T
— 93 points à un jour, soit **155 fois** le stop déclaré. Trois natures :
mécanique, réglage d'affichage, choix d'ancrage (le retracement est un prix
exact, mais le balancement retenu ne l'est pas : 3,39 points d'écart mesurés).
La probabilité que le stop parle avant le niveau vaut `w/(a+w)`, et **une seule
des neuf lectures passe les deux verdicts** (µ* dans le domaine *et* preuve à
portée) : le nœud de faible volume.
④ **L'identité gamma-thêta.** `Θ = −½σ²S²Γ` : le mouvement d'équilibre vaut
`σ/√365` à toute échéance et à tout strike — le théorème d'arrêt optionnel du
marché d'options. Les deux façons de tenir compte d'une nuit **encadrent la
vérité par les deux côtés**, et leur rapport vaut 1,77 au dernier jour :
*l'approximation quadratique échoue exactement là où le gamma est le plus
grand.*
⑤ **Le signe que la reconstruction jette.** `GEX` suppose le teneur long les
calls et court les puts à tous les strikes ; l'intérêt ouvert ne porte aucun
signe. À signe inconnu la bascule occupe 1 219 points — 135 fois le stop
élargi — et **dans la moitié des tirages elle n'existe pas du tout**. Verdict
calculé : deux affirmations déplacent l'horloge, une le risque, deux rien, et
aucune le sens.

Sa **partie XX** part du premier document de la même série d'options, celui
consacré au delta — `grandeurs.py` + `figgra.py`. Il observe que les
opérateurs emploient un seul mot pour trois grandeurs, et le dépôt découvre
d'abord que l'observation le concerne.

① **Une cible a trois probabilités**, toutes exactes et toutes appelées de la
même façon : la toucher avant le stop (`a/(a+b)` = 4,76 %), la toucher à un
moment (`2Φ(−b/σ√T)` = 62,7 %), clôturer au-delà (31,3 %). **Un facteur 13.**
Le mécanisme ne se comprend pas d'une liste : la partie montre **trois séances
simulées**, dont celle qui prend le stop dans la première minute puis atteint
la cible à la minute 360. Ce cas-là n'est pas une curiosité — il vaut **55,5 %
des séances**, contre 6,6 % pour la cible atteinte avant le stop.
② **Le coût est calculable et énorme.** Portée dans l'identité de Wald, la
deuxième rend +11,61 R quand la vraie rend −0,550 R : **12,2 R d'écart par
décision**, et il ne dépend pas de la friction. Le taux d'équilibre (7,38 %)
tombe *entre* les trois — c'est pourquoi l'erreur survit : elle ne déplace pas
un chiffre, elle retourne le verdict.
③ **Un delta en a trois aussi** — `e^{−qT}N(d₁)`, `N(d₂)`, `−∂V/∂K`. L'écart
vaut 22,3 points de delta à 80 % et six mois, quand le document extérieur
annonçait « plus de 15 » : son annonce était prudente. La coupure est celle de
① à l'identique — `N(d₁)` pondère par le chemin, `N(d₂)` ne regarde que le
terme.
④ **Le charm**, seule grandeur qui déplace une position sans que le marché
bouge. Le document dit qu'il « domine dans les derniers jours » ; la mesure
raffine : **à la monnaie il est 94 fois plus petit qu'à son pic**, et le pic
se referme sur le strike (9,7 % à 60 jours, 1,3 % à un jour). Lieu en forme
fermée `d₁* = (σ√T ± √(σ²T+4))/2`, contrôlée contre un balayage.
⑤ **Deux livres de delta net nul, paris opposés**, 0,55 % de notionnel d'écart
sur 2 %. Le Calmar de la partie XVIII cachait sa bande ; le delta net cache sa
courbure.
⑥ **Trois conventions**, et deux mécanismes d'ordres différents : le portage
donne 0,40 point, l'ajustement de prime 7,0 et jusqu'à 47,5. **Et
`V/S = Δ − N(d₂)` exactement à la monnaie** — les deux confusions de la partie
sont un seul nombre portant deux noms, et l'identité tombe hors de la monnaie.

Cinq pièges y sont enterrés. Les trois probabilités étaient publiées **sans
contrôle par simulation**, ce que la règle du dépôt interdit sans exception :
mille cinq cents séances au douzième de minute les confirment maintenant, et
elles rendent un fait gênant. Une barrière surveillée à pas fini est franchie
moins souvent qu'une barrière continue — l'écart vaut `β₁·σ√Δt`, la constante
de la partie XVI, importée et non recopiée — et **le stop déclaré est si
étroit que cette correction vaut 35 % de sa largeur** : aucune grille
raisonnable ne le résout, et seules les deux quantités lointaines y sont
confirmées. La géométrie de contrôle (stop 6 points) existe pour cela, et les
trois formes y tombent sur la mesure. Le quatrième piège est dans la planche
d'exemple : la minute où la trajectoire atteint la cible est la **première
traversée**, jamais la minute du maximum, et le premier jet publiait la
seconde en croyant publier la première (378 au lieu de 360). Et les deux
livres n'étaient **pas** à delta nul :
le delta d'un straddle s'annule un peu au-dessous du strike, et le premier jet
avait écrit « +0,00 » à la main au lieu de le calculer ; les livres sont
maintenant couverts et le zéro est recalculé. Le relief du charm portait
d'abord l'amplitude contre la volatilité, et la mesure a corrigé la phrase :
l'axe n'est pas mort, il est **cent fois plus faible** que celui de l'échéance
(facteur 154 contre 1,6), et un test compare désormais les deux étendues au
lieu d'affirmer la platitude de l'une. Et la table des conventions balayait le
portage en rendant une colonne constante, parce que l'ajustement de prime — qui
domine — ne dépend ni du taux ni du dividende.

Deux pièges y sont enterrés. Le relief du signe portait d'abord l'asymétrie du
profil en second axe, avec un mécanisme plausible écrit d'avance — la masse
d'un côté devrait finir par dominer. **La mesure rend une surface plate** (975
à 1 072 points sur toute la plage), l'axe a été remplacé par l'échéance, qui
agit, et un test exige désormais que l'asymétrie ne resserre rien. Et la
largeur de bande est **censurée** : une configuration sans bascule n'entre
dans aucun quantile, donc la bande mesurée est une borne inférieure de
l'incertitude — et elle l'est le plus là où l'incertitude est la plus grande.
Le relief porte donc la part d'absence, la seule grandeur que la censure ne
fausse pas.

Sa **partie XXI** poursuit la série d'options par le guide consacré au thêta —
`theta.py` + `figth.py`. Il s'ouvre sur la phrase la plus juste des trois :
*le thêta est le loyer de la convexité, et les deux ne se séparent pas.* Le
dépôt souscrit et va là où le guide s'arrête : si les deux ne se séparent pas,
le vendeur n'encaisse pas un revenu, **il encaisse une fréquence.**

① **La loi nulle d'un vendeur de prime**, et c'est le résultat structurant.
Sur un intervalle de couverture, le vendeur gagne si `Z² < 1` : la fréquence
vaut **2Φ(1) − 1 = 68,3 %**, sans référence au strike, à l'échéance, à la
volatilité ni au niveau, et le mécanisme est la médiane d'un khi-deux à un
degré (0,455) comparée à sa moyenne (1). Mais la fréquence **descend vers un
demi** quand les séances s'empilent — forme fermée `P(χ²ₘ < m)`, contrôlée
par simulation — et la position de trente jours y est déjà (51,0 % mesuré).
*Le relevé du soir et la position ne sont pas le même objet, et c'est le
premier qu'on regarde.* Le vendeur nu, lui, garde 57,5 % parce que son
résultat est un événement terminal et non une somme.
② **Ce que la couverture achète.** À couverture continue et réalisée égale à
l'implicite, le résultat est *identiquement* nul : toute la dispersion vient
de la discrétisation. L'exposant est **ajusté et non postulé** (0,487) — la
partie XVIII a payé pour cette règle — et ni l'espérance ni la fréquence de
gain de la position ne bougent avec le pas de couverture.
③ **Les deux horloges.** Le guide publie son propre test — trois jours de
décroissance annoncés sur un week-end, « plutôt un » observé — et cette
observation **calibre** le seul paramètre non observable du modèle,
`ω = 0,2566`, exactement comme les deux nombres sans direction calibraient la
partie XV. La prédiction qui en sort est que le nombre de jours apparents ne
dépend **pas** de l'échéance, parce que la valeur décroît comme la racine du
temps — *et c'est le point où le guide se contredit, ayant consacré une
section entière à cette racine.* À poids calibré, la hausse d'implicite du
lundi se réduit à `√((D−1)/(D−3)) − 1`, contrôlée contre la route générale :
3,6 % à trente jours, 73 % à quatre, et elle dépasse une fourchette d'un point
de volatilité **sous 28 jours**.
④ **Le signe.** La frontière du thêta positif se calcule, et la région a une
propriété que le guide n'écrit pas : **à taux nul elle est vide**, exactement,
puisque le terme qui la crée est proportionnel à `r`. L'avertissement « vérifiez
le signe » n'a rien coûté à personne pendant la décennie des taux nuls.
⑤ **Le budget d'information d'une prime de variance.** Un point d'écart
implicite-réalisé demande 55 expirations, soit 4,5 ans à une par mois — le
budget de la partie IV, rencontré sur un objet entièrement différent. Et le
croisement calculé : il faut **1,6 point d'avantage** pour qu'un mois affiche
ce qu'une soirée sans le moindre avantage affiche déjà.
⑥ **Le décompte**, compté et non écrit : quatre affirmations déplacent
l'horloge, trois le risque, une rien, **une seule touche à la direction — et
c'est celle qui dit qu'il n'y en a pas.** Sur les dix-neuf affirmations des
trois parties d'options, aucune ne donne un sens.

Cinq pièges y sont enterrés, et quatre n'ont été vus qu'en regardant la page.
L'**appariement antithétique** y est légitime — la loi est symétrique — et
**parfaitement inutile** : la corrélation entre un chemin et son symétrique
vaut 0,98, parce que le bilan d'une couverture delta est une fonctionnelle
presque paire ; il ne réduisait aucune variance et divisait l'échantillon
effectif par deux. C'est l'autre piège du geste que la partie XIV interdit sur
une loi asymétrique. L'**épaisseur d'une barre est en pixels**, jamais en
unités de donnée : passée en unités de donnée elle valait trois centièmes de
pixel et les deux histogrammes se réduisaient à des cheveux — invisible aux
trois balayages. Un **domaine écrit à la main** posait la courbe de gamma
*entièrement hors du cadre*, et c'est le test d'enveloppe de `Panel.path` qui
l'a trouvée, pas l'œil. `_dec` **perdait le signe de l'exposant** : « 10¹ »
pour un dixième et « 10¹ » pour dix, sur le même axe. Et le titre d'un cadre
est mis en capitales par la feuille, donc **`σ` s'y publie `Σ`** — la formule
va dans la lecture chiffrée, qui reste en bas de casse.

Sa **partie XXII** poursuit la série d'options par le guide du véga —
`vega.py` + `figvg.py`. Il s'ouvre sur une phrase que les trois autres n'ont
pas : *le véga mesure la sensibilité à un paramètre que le modèle suppose
constant.* C'est un aveu de circularité, et le dépôt en connaît le prix.

① **Trois nombres publiés, deux réfutés.** Le véga croît en `√T` — vrai, les
deux courbes sont indiscernables — mais le rapport d'un an à deux semaines
vaut **5,07** et non 5,5. « Le gamma est une pointe, le véga une colline » est
**faux** : les deux pics partagent `φ(d₁)` et mesurent la même largeur à un
pour cent près ; ce qui s'inverse est la hauteur, et leur rapport est une
identité — `Γ/V = 1/(S²σT)`, **indépendante du strike**, qui composée avec
celle de la partie XIX donne `|Θ₁|/V = σ/2T`.
② **Deux livres à véga net calculé nul**, comme les deux livres de delta de la
partie XX. Chacun vit d'un mode de surface et reste aveugle à celui de
l'autre ; et sous un choc de **niveau**, où le véga annonce zéro à juste
titre, le livre d'ailes perd **0,284 point d'indice** sur les dix points de
l'exemple du guide. Cette perte-là n'a aucun véga.
③ **La pondération en `√(30/T)`**, que le guide appelle le correctif standard,
est un exposant **postulé** — la faute de la partie XVIII. Le verdict porte
plus loin que sa valeur : sous une volatilité à retour à la moyenne, la
sensibilité d'un ténor vaut `(1 − e^{−κT})/(κT)`, dont l'exposant local passe
de zéro à un et ne vaut un demi qu'à **un seul** ténor. *Une loi de puissance
n'a pas d'échelle et cette courbe en a une* : le minimum de l'écart maximal
est atteint à κ = 7,77/an et laisse encore **39 %** d'écart aux deux bouts.
Aucune vitesse ne sauve la règle.
④ **La bande où la courbure change de signe** est `[e^{−σ²T/2}, e^{+σ²T/2}]`,
donc `σ²T` de large : **0,51 % du spot à trente jours**, et aucun strike d'une
grille au pas d'un pour cent n'y tombe au-dessous de quinze jours. *Au sens de
la courbure, il n'existe pas d'option à la monnaie sur le tableau.*
⑤ **Le seuil d'un vendeur de véga**, et c'est l'identité du document sur un
quatrième objet : `µ*_σ = −½·(volga/V)·s²`, la baisse d'implicite qu'il faut
rien que pour ne rien perdre. Nulle à la monnaie, **0,55 point par mois** sur
une aile à quatre-vingt-dix jours. La forme fermée, du second ordre, la
sous-estime de 17 % — le défaut de la partie XIX, au même endroit.
⑥ **« Cela paie la plupart du temps, et les pertes sont concentrées »** : les
deux moitiés tombent. Le prix d'une option est **monotone** en volatilité,
donc la fréquence vaut **exactement un demi** à toute moneyness et à toute vol
de vol, pour une espérance négative. Et les cinq pour cent de pires mois
portent 26,9 % des pertes contre 25,7 % sous une gaussienne de même
dispersion : *sous une variation d'implicite gaussienne, la concentration d'un
vendeur est celle d'une gaussienne* — la phrase décrit la queue de
l'implicite, pas la position.
⑦ **Le budget**, le plus lourd des quatre : un point d'avantage par mois
au-delà du seuil demande **10,5 ans**, et à cet avantage-là la fréquence de
gain ne monte qu'à 60 %. Sur les **vingt-huit** affirmations des quatre
parties d'options, aucune ne donne un sens.

Deux pièges y sont enterrés, et le premier est le plus instructif de la
session. Le domaine d'un cadre se déclare **avant** les tracés : déclaré
après, les courbes se dessinent dans le domaine par défaut et le découpage les
réduit à un point — ni le balayage de débordement ni celui d'occupation ne le
voient, et c'est le test d'enveloppe de `Panel.path` qui l'a trouvé. Et un
cadre borné à la main affichait un **plateau qui n'existait pas** sur la
courbe de l'écart maximal, parce que `min(1.05, ...)` écrasait tout ce qui
dépassait.

Sa **partie XXIII** poursuit la série d'options par le guide du rho —
`rho.py` + `figrh.py`. C'est le plus honnête des cinq sur son propre objet :
il s'ouvre en disant que pour un opérateur intrajournalier sur indice liquide,
*rho est négligeable et le traiter comme tel est correct*, puis il explique où
ce raisonnement casse. Le dépôt ne le conteste pas — il le chiffre, et la
correction la plus lourde ne porte sur aucun nombre.

① **`ρ = KTe^{−rT}N(d₂)`, et la proportionnalité qui s'use.** L'exposant local
vaut un jusqu'à trois mois, **0,95 à un an, 0,91 à deux ans**, et la droite du
mois s'écarte de cinq pour cent dès 403 jours. Rho passe par un **maximum** à
24,1 ans. Le premier jet écrivait que ce maximum vaut `1/r` ; **un test l'a
refusé** — à 2 % la phrase se trompe d'un tiers — et la correction est le
résultat de la section : le lieu ne vaut `1/r` qu'au seul taux
`r* = q + σ²/2` = 4,42 %, celui auquel une option à la monnaie a la même
chance d'être exercée à toute échéance ; au-dessous il vient plus tôt,
au-dessus plus tard, et **il existe encore à taux nul** (45 ans), poussé par
la seule décroissance de la probabilité d'exercice. Les deux nombres publiés
sont justes — 0,0408 à un mois, 0,9054 à deux ans — mais leur rapport vaut
**22,2** et non les deux ordres de grandeur annoncés.
② **Le croisement avec le véga, et la faute qui décide de tout.** Trois routes,
trois siècles. Point de taux contre point de volatilité : **237 jours**. Mais
un point de taux et un point d'implicite ne se produisent pas à la même
fréquence — l'implicite du mois bouge 19 fois plus — et pondéré par la
dispersion de chaque moteur, le croisement **sort de toute échéance
négociée**. Il n'y revient qu'en tenant compte de ce que le guide n'écrit
pas : la volatilité longue bouge moins que la courte. Avec le poids ajusté de
la partie XXII, il tombe entre **1,2 et 4,1 ans**. *L'affirmation est vraie
sur une route des trois, et le guide ne dit pas laquelle.* La leçon dépasse le
rho : comparer deux sensibilités, c'est comparer deux moteurs.
③ **« Un risque ignoré à 0 % n'est pas ignorable à 5 % »** est la même faute
vue de l'autre bout. La sensibilité croît de **23 %** sur toute la plage de
taux, et dans le sens inverse de ce que la phrase suggère. Ce qui a changé de
plusieurs ordres est la dispersion du moteur.
④ **Le rho change de signe** selon la variable qu'on tient fixe, et le guide
s'arrête juste avant de l'écrire. À spot fixe, +0,905 sur deux ans ; à forward
fixe, **−0,321**, soit exactement `−T·V` — contrôlé en bougeant le taux et le
spot ensemble. L'écart vaut 1,226 point par point de taux sur une seule
option, et les deux lectures ne convergent nulle part.
⑤ **Une option très dans la monnaie est une action financée**, et c'est exact :
à deux fois le strike l'écart vaut 0,28 % et le rho atteint 97 % de son
plafond `KTe^{−rT}`. Le plafond éclaire la forme entière — la part atteinte
**est** `N(d₂)` — et le fait le moins attendu en sort : à la monnaie, cette
part *décroît* avec l'échéance.
⑥ **Ce que rho coûte à l'opérateur de ce document** : le rho d'une position
ouverte et fermée dans la séance déplace **22 086 fois** moins que la friction
déclarée. Ce n'est pas un petit terme, c'est un terme qui n'existe pas — et il
n'atteint la friction qu'au-delà de dix ans d'échéance dans un régime de
resserrement.
⑦ **Le décompte** : quatre affirmations déplacent le risque, une l'horloge,
deux rien, et **aucune la direction**. C'est la première des cinq parties dont
cette colonne est vide, et rho est aussi le seul des grecs dont le moteur ne
soit pas le prix. Sur les **trente-cinq** affirmations de la série d'options,
aucune ne donne un sens.

Trois pièges y sont enterrés. Le premier est celui du `1/r` ci-dessus, et sa
leçon est générale : **une forme fermée qui « tombe à peu près » quelque part
n'en est pas une** — ici la vraie condition est une égalité exacte entre le
taux, le rendement et la moitié de la variance, et c'est un test écrit avant
d'y croire qui l'a fait apparaître. Le second est une bissection dont la borne
haute (200 ans) coupait le maximum à taux nul, qui tombe à 45 ans mais monte
au-delà de la borne pour des volatilités plus basses. Le troisième est un
format : la part de friction d'une position intrajournalière publiait
**« 0,0000 »** sur quatre décimales, c'est-à-dire qu'elle effaçait le résultat
de la table au lieu de le montrer ; `_part` donne maintenant deux chiffres
significatifs, et un test refuse le zéro trompeur.

Quatre autres n'ont été vus qu'en **regardant la page** (partie XXIII), et aucun ne l'aurait
été autrement. Les trois risques du croisement parcourent trois ordres de
grandeur : tracés en échelle linéaire, le plus grand écrasait les deux qui se
croisent, et *le croisement — le sujet du cadre — était invisible*. Le
contrôle par différence finie du rho à forward fixe se superpose exactement à
la forme fermée, ce qui est le résultat du cadre ; tracé en pointillé sombre
sous un trait clair, il disparaissait et la planche ne montrait plus qu'une
courbe — il passe maintenant **dessous**, en clair, et la forme fermée
par-dessus en pointillé sombre. Une légende de relief annonçait « la vallée où
le croisement passe sous quelques années » sur une surface qui n'a pas de
vallée, et un plafond « à soixante ans » qui ne mord nulle part : les deux
sont remplacés par des comptes calculés. Et l'arête d'un relief étiquetait
quatre-vingt-dix jours **« 0 »** année, faute d'une décimale.

Sa **partie XXIV** poursuit la série d'options par le guide du vanna —
`vanna.py` + `figva.py`. C'est le seul des six à publier **le résultat de son
propre test**, contre un niveau témoin placé à la même distance de
l'ouverture : exactement le contrôle que la partie XIX avait dû ajouter au
guide du gamma. Sur ce point le dépôt n'a rien à corriger ; il a de quoi
chiffrer. Et la vérification a d'abord trouvé un défaut **ici**.

⓪ **Le défaut du dépôt, et pourquoi la règle existe.** `vega.vanna` écrivait
`−𝒱·d₂/(Sσ)`, dont le dénominateur oublie `√T` : elle rendait le vanna
multiplié par la racine de l'échéance — trop petit d'un facteur **3,5** à
trente jours, juste à un an, trop grand au-delà. *Rien ne l'avait vu parce que
rien ne la consommait* : aucune table, aucune figure, aucun test. La règle du
dépôt — une forme fermée se contrôle contre une route indépendante — avait été
appliquée au véga et à la volga mais pas à leur dérivée croisée. **Elle vaut
aussi pour ce dont personne ne se sert encore**, et le contrôle idéal était là
depuis le début : `∂Δ/∂σ` et `∂𝒱/∂S` sont le même nombre par la symétrie des
dérivées secondes, donc l'égalité ne peut échouer que si le code est faux.
① **Le zéro, et le taux qui décide de son côté.** Il tombe où `d₂ = 0`, donc
au-dessus de la monnaie **si et seulement si `r < q + σ²/2`** — le même
`4,42 %` que la partie XXIII a trouvé sur le maximum du rho, par une route
sans rien de commun.
② **« Le vanna ramène le delta vers un demi » échoue deux fois.** D'abord sur
`d₂ < 0 < d₁`, qui est *exactement* la bande de volga négative de la partie
XXII : les deux guides décrivent le même ensemble sans le savoir, largeur
`σ²T`, 0,52 % du comptant à trente jours — donc sous le pas d'une grille de
strikes. *Une réfutation qui confirme.* Ensuite parce qu'à volatilité qui
croît le delta tend vers `e^{−qT}`, pas vers un demi : il descend, s'arrête
sur un plancher `e^{−qT}N(√(2 ln(F/K)))`, puis remonte. Le retournement se
calcule — `σ* = √(2 ln(F/K)/T)` — et il tombe à **38,9 %** sur un call à cinq
pour cent dans la monnaie et un an, *dans le domaine plausible*.
③ **Le déplacement annoncé.** « De 15 % à 45 %, un vingt-deltas en vaut trente
environ » : la mesure rend **41**, la propre tangente du guide en rendrait 69,
et trente s'atteignent à **23,2 %** — huit points de choc et non trente.
L'effet est *plus grand* que ce qu'il en dit.
④ **Le pic, et la fenêtre.** Son lieu est `d₁* = (σ√T − √(σ²T+4))/2`, **la même
racine que le pic du charm** de la partie XX (les deux valent `φ(d₁)` fois une
fonction affine de `d₁`), importée et non recopiée. Il se tient à un **delta
presque constant** (16 % à un jour, 21 % à cinq ans) et migre donc vers
l'extérieur en `√T`. Le module croît **de bout en bout** : « aux échéances
intermédiaires » décrit la fenêtre `0,80–1,20` de la planche du guide, d'où
l'arête sort par le côté. *Le piège de la légende écrite devant un cadre
borné, trouvé cette fois dans une figure qui n'est pas la nôtre.*
⑤ **La formule nomme le mauvais grec.** `Δ + vanna·∂σ/∂S` n'est pas un delta —
inverse de volatilité fois volatilité par point donne un inverse de point. La
correction juste porte le **véga** et reproduit une réévaluation le long de la
peau à la quatrième décimale ; celle du guide en capte **0,07 %**, et *change
de signe* au-dessus de la monnaie. Sa formule est celle du **gamma** effectif
portant le nom du delta, et même là il lui manque un facteur deux et le terme
de volga : `Γ + 2·vanna·σ′ + volga·σ′²` referme l'écart à la sixième décimale.
Le graphique posé dessous, lui, est juste.
⑥ **Le test, et l'agrégation.** Le témoin apparié en distance de la partie XIX
rejoué : le taux de touche ne dit que la distance, le taux de réussite vaut
`1/(1+R:R)` partout, donc un niveau agrégé ne bat son témoin qu'en déplaçant
`µ`. *Le résultat négatif du guide est ce que la loi nulle prédisait.* Puis un
fait qui vient avant tout tirage : **sous l'hypothèse de signe du guide, le
profil agrégé traverse zéro deux fois** quand le GEX n'en traverse qu'une — le
gamma est positif à tous les strikes, le vanna change de signe en chacun.
« La » ligne de vanna n'est pas un objet défini. Signe inconnu, le verdict est
**l'inverse de celui de la partie XIX** : le GEX échouait par *absence* (la
moitié des tirages sans bascule), le vanna échoue par *abondance* — 57 % des
tirages en portent trois ou plus, sur 1 381 points, 153 fois le stop élargi.
⑦ **Les notes de pupitre.** La première se **renforce** : le véga net d'un risk
reversal symétrique en delta n'est pas « quasi nul », il est *identiquement*
nul, parce que le véga ne dépend de `d₁` que par la fonction **paire** `φ` et
que les deux strikes ont des `d₁` opposés. La troisième tombe sur le piège que
la quatrième annonce : sous la convention que le guide définit lui-même, une
aile de put vendue est **longue** de vanna, non courte.
⑧ **Le décompte** : cinq affirmations déplacent le risque, trois rien, aucune
l'horloge, **aucune la direction**. Sur les **quarante-trois** affirmations
des six parties d'options, aucune ne donne un sens.

Deux pièges y sont enterrés, en plus de celui du dépôt. Une bissection posée
sur une boîte dont les deux bouts sont du même signe rend « pas de ligne » là
où il y en a deux : le premier jet de `ligne_de_vex` l'a fait, et le remède est
`lignes_de_vex`, qui **balaie et rend toutes les traversées**. Et une
hypothèse écrite d'avance est **réfutée par la mesure** : on attendait que le
second inobservable — la volatilité vraie par strike — élargisse la bande. Il
ne l'élargit pas, le signe la domine entièrement ; il fait autre chose, qui
n'avait pas été prévu, et que la table publie : il **multiplie les lignes**,
de 57 % à 88 % de tirages à trois lignes ou plus.

Sa **partie XXV** ferme la série d'options par le guide du charm —
`charm.py` + `figch.py`. C'est le seul des sept dont l'usage recommandé **ne
demande aucun signe**, et l'encadré qui le dit est la meilleure chose des sept
documents. La correction la plus lourde, elle, n'oppose pas ce guide au
dépôt : **elle l'oppose au guide du thêta de la même série.**

① **L'accélération, et la puissance qu'on lui prête.** Le guide lit le
`T^{3/2}` de son dénominateur et en conclut que le charm « accélère fort ».
Le numérateur porte `d₂σ√T`, qui en annule la moitié : l'exposant mesuré de
l'amplitude au pic vaut **−0,99**, c'est `1/T`, et l'asymptote est la forme
fermée `φ(1)/(2T)` que la partie XX avait déjà établie.
② **Le pic n'est pas à vingt-cinq deltas** mais à **seize et quatre-vingt-cinq**,
en forme fermée : `d₁* = (σ√T − √(σ²T+4))/2`, la racine de la partie XX, **la
même que le pic du vanna** de la partie XXIV. Et le guide illustre son propre
mécanisme sur un call à 4 % hors de la monnaie qui, à un jour, porte `0,0009`
de delta — *il n'a plus rien à perdre*. Le phénomène vit à 1,3 % de la monnaie.
③ **« La ligne à la monnaie reste près de zéro »** : elle **diverge** aussi, en
`1/√T` quand le pic diverge en `1/T`. Ce qui reste près de zéro n'est pas une
quantité, c'est un rapport — 51 à un jour, **10 à trente**.
④ **Le week-end, et c'est le résultat de la partie.** Le charm guide dit trois
jours de saignée pour un jour de variance ; le **guide du thêta de la même
série** a publié l'observation qu'un week-end fait voir *un* jour, et la
partie XXI en a tiré `ω = 0,2566`. Sous cette horloge la saignée vaut **le
tiers au quart** de la lecture calendaire, et l'écart est le plus grand **sur
les ailes** — là où le guide dit que les positions dérivent le plus. À `ω = 1`
on retrouve exactement sa lecture, facteur un : *c'est le plancher du relief,
donc toute autre hypothèse la rend surestimée.*
⑤ **Le coût de couvrir au delta du soir.** « Réévaluez sous deux semaines » :
la règle est juste et le seuil trop court — le coût passe sous la friction
déclarée à **31 jours**. Troisième fois de la série qu'un guide se
sous-estime, après les 22,3 points de delta de la partie XX et les 41 deltas
de la partie XXIV.
⑥ **Le strangle ne saigne pas symétriquement.** Les deux jambes ont des `d₁`
opposés, donc leur somme laisse **`−φ(z)·σ/√T`** — une forme fermée nulle à
aucun delta ni à aucune échéance, contrôlée à huit décimales. Les deux jambes
perdent leur delta et *le livre raccourcit en le faisant* ; la part non
compensée va de 5 % à **89 %**. Le vertical ne compense pas davantage : la
différence est un rapport de deux ou trois, qui s'inverse au-delà de quelques
mois.
⑦ **L'agrégation, et la seule affirmation de la série qui tienne.** Le gamma
agrégé demandait **un** inobservable et faisait errer son niveau sur 135 stops
élargis ; le vanna en demandait **deux** et rendait trois lignes ; le charm
n'en demande **aucun**, parce qu'il s'emploie sur un livre qu'on connaît. Le
guide le dit, et il dit aussi que le même objet employé comme niveau de marché
hérite de tout. **Sur les sept documents, c'est la seule affirmation
d'agrégation que le dépôt reprend.**
⑧ **Le décompte** : trois affirmations déplacent le risque, trois l'horloge,
deux rien, **aucune la direction** — troisième partie consécutive dans ce cas.
Sur les **cinquante et une** affirmations des sept parties d'options, aucune
ne donne un sens.

Deux pièges y sont enterrés. Le premier est un **pas de quadrature** : la
première version de `temps_de_marche` intégrait l'horloge par pas de 0,05
jour, et la quantisation faisait sauter le delta d'un dixième au bord du
cadre ; la fonction est maintenant analytique, et c'est en regardant la
planche qu'on l'a vu. Le second est le **dernier instant d'une option** : à
`T → 0` le delta est une marche, et une formule y rend une valeur gouvernée
par le portage plutôt que par la position — la planche s'arrête donc un
dixième de jour avant l'échéance, faute de quoi la ligne à la monnaie
publiait un saut de 0,50 à 0,80 qui n'existe pas.

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
- `setups.py` — **la grammaire du setup.** `NIVEAUX` (6, causaux, calculés sur
  la première demi-séance ou sur le passé à la minute), `CONFIRMATIONS` (3,
  cinq seuils déclarés), `SETUPS` (12), `seances()` à la barre avec graine
  **par minute** — c'est ce qui rend `footprint(seance, minute)` rejouable et
  interdit à une figure de montrer autre chose que ce que la table mesure.
  `criteres()` est la source unique : `_confirme` en découle, et les cases
  cochées d'une planche aussi. `_independants()` porte l'embargo (voir le
  piège plus bas). `poule()` met les douze en commun — c'est là, et pas dans
  une cellule isolée, que le résultat se lit.
- `figsetup.py` — les six planches du setup. `setfoot` (le footprint au point
  de contrôle, trois confirmations, critères cochés par la mesure),
  `setprofil`, `setdow`, `setvwap`, `setcout` (le délai, de brut à confirmé),
  `setrelief` (la surface). `_seance_temoin` choisit la séance montrée par une
  règle calculée : la première qui porte un exemple de chaque confirmation.
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
- `overnight.py` — **une affirmation venue du dehors, passée au protocole.**
  `ANNONCES` (les sept nombres publiés, cités une seule fois), `nuits()` (la
  position d'ouverture, grandeur **sans dimension**), `profil()` (pic de
  variance d'ouverture, à variance totale identique), `calibrer()` sur
  `CALIBRAGE` — et un test exige que les cibles de calibration ne portent
  aucune direction. `taux_equilibre()` et `esperance_au_taux()` permettent de
  **supposer le chiffre publié vrai** plutôt que d'avoir à le croire.
- `robustesse.py` — **l'invariance sous six lois de prix.** `lois()`,
  `moments()`, `queues()`, `mesurer(drift)`, `Z_SEUIL` (Bonferroni calculé),
  `cellule()` et les deux surfaces. Le champ `symetrique` décide de
  l'appariement antithétique et un test l'exige. **Toutes les cellules des
  surfaces voient le même flux d'aléa** — la graine ne dépend que de l'indice
  de trajectoire — et c'est ce qui rend le relief lisse sans lissage.
- `pieds.py` — la prose de pied sort du SVG et se recompose sous la figure.
  **Les quatre documents y passent** ; `paper.py` et `paper2.py` ne le
  faisaient pas, faute de pouvoir importer `workingpaper` sans cycle. Deux règles y sont enterrées :
  une ligne de pied non finale doit finir sur une virgule, sinon le raccord
  la ponctue et coupe la phrase ; et toute phrase qui commence prend sa
  majuscule, sauf si elle ouvre sur une lettre grecque — `µ` capitalisé
  donnerait `Μ`.
- `emprunts.py` — **les cinq disciplines empruntées.** Seize tables. Trois
  formes fermées y sont contrôlées contre la simulation et c'est ce qui les
  rend publiables : `survie_minute` (correction de continuité de
  Broadie-Glasserman-Kou, `β₁ = 0,5826`), `amplitude_palm`
  (`α(2β−α)/2(β−α)`, dont l'intégrale doit rendre le rapport de Fano) et
  `pic_hasard` (voir le piège plus bas). `hawkes()` simule par amincissement
  d'Ogata ; `fenetre_temoin()` choisit la fenêtre montrée par une règle
  calculée. Six surfaces, toutes maximum au fond.
- `figemp.py` — les quinze planches de la partie XVI, dont six reliefs.
- `fonds.py` — **ce qu'un fonds fait, et ce qui en reste.** `ANNONCES` (les
  trois nombres publics, cités une seule fois), `ic_requis`, `taux_de_ic`
  (conversion **exacte** pour un pari binaire), `seuil_de_credibilite`,
  `ic_combine` et son `plafond`, `impact_racine` (loi en `√Q`, `Y` déclaré),
  `capacite()` par bissection, `glissement_sortie()` — qui n'est **pas** posé
  à la main mais vaut `(1 − p_cible)·1,5` tick, et sous-facturer cette
  quantité est l'erreur de budget la plus fréquente. Huit tables, quatre
  surfaces.
- `figfds.py` — les dix planches de la partie XVII, dont quatre reliefs.
- `revue.py` — **deux documents venus du dehors, et rien que leurs nombres.**
  `DOC_A` / `DOC_B` (les deux jeux publiés, recopiés une seule fois), et
  quatre familles de mesures. Les identités de cohérence (`vol_implicite`,
  `marche_implicite`, `n_implicite` — un couple corrélation/statistique publie
  la taille d'échantillon sans le vouloir, et elle tombe sur la période
  annoncée). La bande d'échantillonnage du Calmar : `tirages`, `bande_calmar`,
  `bandes_par_prefixe` (l'astuce du préfixe, voir plus haut), `loi_de_bande`
  qui **ajuste** l'exposant au lieu de le postuler, `annees_pour_ecart`. La
  dépendance de queue : `rho_du_saut`, `n_pour_rho` / `rho_detectable` par
  Fisher, `melange` où le saut est **compensé** — sans quoi la dépendance
  changerait aussi le rendement — et `taille_invisible`, le nombre qui manque
  à toute note concluant à l'indépendance. Le portage : `cout_admissible`,
  `marge_de_cagr`, `facteur_fatal = 1 + marge/budget`, qui **décroît** avec le
  budget. La capacité : `capacite_pure` en `ν⁻²` exact, `capacite` avec la
  friction fixe, `rotation_fatale`. Neuf tables, quatre surfaces.
- `figrev.py` — les dix planches de la partie XVIII, dont quatre reliefs.
- `niveaux.py` — **la largeur d'un niveau, et le témoin apparié en distance.**
  `taux_de_touche` (réflexion), `taux_de_reussite` / `_ferme` (les deux routes,
  et leur accord est le contrôle du module), `taux_de_tenue` = `e/(r+e)`,
  `cloture_avant_barriere` (la condition, publiée en colonne), `exces_requis`
  et `touches_requises` (les deux identités, contrôlées contre `entropy`),
  `largeur_gamma` (`√(2 ln 2)·σ√T`), `invalidation_prematuree` = `w/(a+w)`,
  `largeur_d_ancrage` (simulée), `niveaux()` **trié par largeur calculée**,
  `geometrie_forcee` / `passe_les_deux`, l'identité gamma-thêta par trois
  routes (`equilibre_instantane` / `_quadratique` / `_exact`), et le bloc GEX
  (`profil_oi`, `gex`, `bascule`, `bande_de_bascule`, `surface_absence`).
  Huit tables, quatre surfaces.
- `fignv.py` — les douze planches de la partie XIX, dont quatre reliefs.
- `grandeurs.py` — **un mot, plusieurs nombres.** Les trois probabilités d'une
  cible (`p_avant_stop` / `_ferme`, `p_touche`, `p_cloture`), `esperance_r` et
  `cout_de_confusion` (qui ne dépend pas de la friction), les trois deltas
  (`delta_comptant`, `proba_terminale`, `dual_delta` — contrôlé contre une
  différence finie sur le strike), `charm` (contrôlé contre une différence
  finie), `d1_du_pic` / `moneyness_du_pic` / `amplitude_asymptotique`, les deux
  livres couverts (`delta_straddle`, `pl_livre`, `delta_net_couvert`), les
  trois conventions et `identite_prime_gap`. Le contrôle par simulation :
  `simuler_issues` (les quatre issues d'une séance, appariées),
  `decalage_continuite` / `p_avant_stop_discret` (la correction de
  Broadie-Glasserman-Kou, importée de `emprunts`), `CONTROLES` (les deux
  géométries), `trajectoires_temoins` (une séance par issue, choisie par une
  règle calculée) et `minute_de_la_cible` — **la première traversée, jamais la
  minute du maximum**. Neuf tables, quatre surfaces.
- `figgra.py` — les quatorze planches de la partie XX, dont quatre reliefs. Elle
  importe `_echine`, `_ticks` et `_dec` de `fignv` plutôt que de les recopier :
  une troisième copie serait une troisième occasion de les faire diverger.
- `theta.py` — **le loyer de la convexité.** `termes_call` / `termes_put` (les
  trois termes séparés, contrôlés contre `theta_numerique`),
  `rapport_theta_gamma`, `taux_par_intervalle` = `2Φ(1) − 1`, `mediane_khi2`,
  `taux_du_vendeur_nu`, `simuler_vendeur` (le couvert, le nu et le relevé
  quotidien, sur les mêmes chemins ; **le bilan d'un intervalle télescope
  jusqu'au résultat de la position**, ce qui rend les deux échelles
  rigoureusement le même objet), `taux_de_m_intervalles` (par `_gamma_p`, la
  gamma incomplète en stdlib), `loi_de_dispersion` (l'exposant **ajusté**),
  `jours_apparents` / `poids_pour_apparents` / `derive_implicite`,
  `frontiere_signe` / `part_positive`, `campagne_prime`,
  `avantage_pour_egaler_la_soiree`, `familles` et `compte_par_grandeur` — les
  décomptes viennent des modules, jamais d'une main. Dix tables, quatre
  surfaces.
- `figth.py` — les quinze planches de la partie XXI, dont quatre reliefs.
- `vega.py` — **le prix de l'incertitude.** `vega` / `volga` / `vanna`
  (contrôlés contre des différences finies), `rapport_gamma_vega` =
  `1/(S²σT)` et `rapport_theta_vega` = `σ/2T`, `largeur_du_pic` et
  `largeur_du_pic_gamma` (la réfutation de la colline), `Ligne` et
  `_neutraliser` (le véga net est **résolu**, jamais écrit), les trois modes
  de surface et `pl_livre` / `pl_au_premier_ordre`, `poids_regle` /
  `poids_modele` / `exposant_effectif` / `kappa_minimax` (aucune vitesse ne
  sauve la règle), `bande_de_courbure` et `strikes_dans_la_bande`,
  `derive_equilibre` et `derive_equilibre_exacte` (les deux routes du seuil),
  `simuler_vendeur` sur **tirages fixés** — ce qui rend l'espérance une
  fonction lisse de la dérive, donc inversible —, `concentration` et
  `concentration_temoin`, `campagne`, `familles` et `compte_par_grandeur`.
  Dix tables, quatre surfaces.
- `figvg.py` — les quinze planches de la partie XXII, dont quatre reliefs.
- `rho.py` — **le taux, et la variable qu'on tient fixe.** `rho_call` /
  `rho_put` / `rho_par_point` et leur contrôle `rho_numerique` ;
  `exposant_effectif` (`d ln ρ/d ln T`), `echeance_du_pic` par bissection et
  **`taux_du_pic_exact` = `q + σ²/2`**, le seul taux où ce maximum vaut `1/r` ;
  `echeance_de_l_ecart`, qui chiffre une approximation au lieu de la
  qualifier. Le croisement avec le véga par trois routes — `croisement_unite`,
  `croisement_brut`, `croisement_structure` — dont la troisième importe
  `vg.poids_modele` et `vg.kappa_minimax` plutôt que de les recopier.
  `rho_forward_fixe` = `−T·V` et son contrôle `rho_forward_numerique`, qui
  bouge le taux **en compensant le spot** : c'est la seule façon de vérifier
  une dérivée à variable tenue fixe. `action_financee`, `rho_plafond`,
  `cout_de_rho` / `echeance_du_cout` rapportés à `FRICTION`, et `_part`, le
  format qui refuse de publier un zéro trompeur. Huit tables, quatre surfaces.
- `figrh.py` — les quinze planches de la partie XXIII, dont quatre reliefs.
- `vanna.py` — **la dérivée croisée, et le contrôle qui manquait.** `vanna`
  (dans `vega`, corrigée ici) et ses deux routes `vanna_par_delta` /
  `vanna_par_vega`, dont l'égalité est la symétrie des dérivées secondes ;
  `moneyness_du_zero` et `zero_au_dessus`, qui importe `rho.taux_du_pic_exact`
  plutôt que de le récrire ; `bande_de_desobeissance` et sa largeur, contrôlée
  contre `vega.bande_de_courbure` ; `vol_du_retournement` et
  `plancher_du_delta`, contrôlé par `plancher_balaye` ; `deplacement` (les
  trois nombres du guide au même endroit) ; `moneyness_du_pic`, qui importe
  `grandeurs.d1_du_pic`, et `vanna_max_fenetre`, qui mesure ce que la fenêtre
  du guide laisse voir ; `delta_reevalue` / `delta_par_vega` /
  `delta_par_vanna` et `gamma_par_vanna`, les quatre lectures de la
  correction de peau ; `lignes_de_vex`, qui **balaie** au lieu de bissecter, et
  `compte_de_lignes` ; `risk_reversal`, dont le véga net est nul par parité.
  Douze tables, quatre surfaces.
- `figva.py` — les quinze planches de la partie XXIV, dont quatre reliefs.
- `charm.py` — **la saignée du delta, et les deux horloges.** `bleed` et son
  contrôle `bleed_numerique` (le temps calendaire s'écoule à l'envers de
  l'échéance, et c'est la seule subtilité) ; `exposant_du_pic` et
  `exposant_a_la_monnaie`, qui mesurent au lieu de postuler ;
  `part_perdue_dans_la_nuit` ; **`POIDS_CALIBRE`, importé de
  `theta.poids_pour_apparents(1.0)`** — le paramètre qui tranche entre les
  deux guides ne vient pas d'ici ; `temps_de_marche` (analytique),
  `delta_sur_horloge`, `saignee_calendaire` / `saignee_horloge` et
  `facteur_du_calendrier`, dont le test exige qu'il vaille **un** à `ω = 1` ;
  `cout_du_delta_du_soir` et `echeance_du_seuil`, rapportés à `FRICTION` ;
  `strangle` et **`strangle_ferme` = `−φ(z)·σ/√T`**, contrôlée à huit
  décimales contre la mesure à portage nul ; `vertical`. Neuf tables, quatre
  surfaces.
- `figch.py` — les quinze planches de la partie XXV, dont quatre reliefs.
- `report*.py` — chacun fournit `values()` et `all_tables()`. `report9` :
  stratégie. `report10` : ALP nº 3. `report11` : le seuil. `report13` : le
  risque refait. `report14` : flux, TPO, information, spectre. `report15` :
  l'audit de l'hypothèse d'edge d'ALP nº 1 — **la colonne de verdict de la
  table `dependance` est calculée, jamais écrite** ; l'ordre des lignes en
  découle, et un test l'exige.
- `fig*.py` — vingt-quatre modules, chacun expose `render_all()`. `figcat.py` porte
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
- `pine/alp1-seuil.pine` — **le seul des trois qui vienne du paper.** Il ne
  donne aucun signal : il affiche `E[τ] = a·b/σ²`, `p(cible) = a/(a+b)`,
  `µ* = c/E[τ]`, l'exigence sans dimension `c/√(a·b)`, le budget en bits et
  l'échantillon requis. Les trois premières sont exactes, pas estimées ; la
  quatrième ne dépend ni de la volatilité ni de l'instrument. La constante
  d'échantillon vaut **4,460 = λ/(2·ln2)** avec λ unilatéral — c'est celle de
  `entropy.trades_for_information`, et l'accord a été vérifié à l'unité près
  sur trois géométries. Aucun `request.*` : il tourne sur le plan gratuit.
  Piège enterré : une friction en ticks seuls sous-estime d'un ordre de
  grandeur le coût sur un actif à cinq chiffres, d'où la ligne en % du
  notionnel.
- `pine/alp0-gex.pine` — report de niveaux gamma. On colle la réponse d'un
  robot Discord ; l'indicateur mesure lui-même la base `NQ − NDX` et la lisse.
  **Ne jamais convertir NDX→NQ à la main : la base saute à chaque roll.**
  Voir `docs/gex-discord-vers-tradingview.md`.
- Ces trois fichiers ne participent ni aux documents ni aux tests : ils n'ont
  pas de loi nulle et n'en revendiquent aucune. **La version déployée sur le
  graphique peut donc diverger de celle du dépôt sans que rien ne le
  signale** — c'est arrivé sur `alp0.pine`, dont le panneau imprimait une
  chaîne absente du fichier. Resynchroniser avant de tirer une conclusion.

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
python main.py --tests      # ~1450 tests (compter ~60 min ; --wp, setups,
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
