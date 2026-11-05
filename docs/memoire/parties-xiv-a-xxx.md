# ALP nº 3 — parties XIV à XXX, détail par partie

> Extrait de `CLAUDE.md` (déplacé tel quel, rien n'est réécrit). À lire quand on touche à ce sujet.

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

Sa **partie XXV** poursuit la série d'options par le guide du charm —
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

Sa **partie XXVI** ferme la série d'options par le guide du volga —
`volga.py` + `figvo.py`. C'est celui qui va le plus loin des huit : il ne
décrit pas une sensibilité, il en tire **une forme de marché**. Le sourire,
dit-il, sort d'une inégalité de Jensen et de rien d'autre — ni peau supposée,
ni flux modélisé. *Le mécanisme est juste.* La route par laquelle il le chiffre
ne l'est pas, et l'écart vaut un facteur.

① **La bande, pour la troisième fois.** `volga = 𝒱·d₁d₂/σ`, contrôlé contre la
dérivée du véga et contre la différence seconde du prix. Le creux « près de la
monnaie » que le guide ne chiffre pas est **exactement** la bande de courbure
de la partie XXII et la bande de désobéissance de la partie XXIV : `σ²T` de
large en logarithme, **0,52 % du comptant à trente jours**, soit 0,51 strike
d'une grille au pour cent. Une nuance que le test a imposée : les trois bandes
ont la **même largeur exactement** et **pas le même centre** — la partie XXII
écrit la sienne en moneyness comptant, celle-ci en moneyness à terme, et
l'écart vaut le portage (0,22 % à trente jours, 2,7 % à un an). *C'est la
question de la partie XXIII sur un quatrième objet : quelle variable tient-on
fixe ?*
② **Le prix à la monnaie est une droite, pas presque.** Sur la plage que le
guide dessine lui-même — cinq à soixante-dix pour cent de volatilité — il
s'écarte de sa corde de **0,10 %** de sa valeur ; à trente pour cent de la
monnaie, de **34,5 %**. La première moitié de l'affirmation se **renforce**.
③ **Trois routes, trois sourires.** Au strike soixante-dix et un mois :
l'inversion au premier ordre rend **53 %**, le second ordre correctement
inversé **29 %**, l'espérance exacte réinvertie **34 %**. Le sourire honnête
vaut **9 points**. Le guide publie la route la plus courte comme une
conclusion.
④ **Le retournement appartient à l'approximation.** La planche du guide montre
trois sourires qui culminent et redescendent ; le sommet du second ordre tombe
au strike **79,5** sur un mois, *dans la fenêtre qu'il dessine*, parce que la
correction de prix est bornée et que le véga qui la reconvertit décroît plus
vite. L'espérance exacte, elle, continue de monter.
⑤ **Le critère de validité pointe à l'envers**, et c'est le fait de la partie.
On borne d'ordinaire un développement du second ordre en exigeant que sa
correction reste petite devant ce qu'elle corrige : ici elle ne dépasse jamais
**1,01 % du prix**, et ce maximum tombe au strike 92,7, *là où les deux routes
sont exactes à deux centièmes de point*. Dans l'aile, où elles se trompent de
quatre et de seize points, elle pèse **0,0002 %**. L'inversion divise par le
véga, et le véga s'annule plus vite que la correction.
⑥ **Vingt points ne coûtent pas deux fois dix** — vrai, c'est le volga — mais
le rapport vaut **4,18 à deux semaines** et **2,08 à six mois**, et le guide
illustre à six mois. *L'exemple affaiblit l'affirmation qu'il illustre*, comme
le strike sans delta du guide du charm.
⑦ **Le papillon n'est pas neutre en véga.** Le véga est maximal à la monnaie,
donc deux ailes ne valent jamais deux corps : un un-deux-un vend **20 %** du
véga du corps à vingt-cinq deltas, **56 %** à dix, et le défaut grandit
précisément quand on croit acheter le plus de convexité. Pondérer les ailes au
rapport des végas (×1,24) annule le véga net **et augmente le volga**, de 57 à
71. La correction ne coûte rien.
⑧ **Le décompte** : six affirmations déplacent le risque, deux rien, aucune
l'horloge, **aucune la direction** — cinquième partie consécutive. Sur les
**cinquante-neuf** affirmations des huit parties d'options, aucune ne donne un
sens.

Trois pièges y sont enterrés, et deux n'ont été vus qu'en regardant la page.
Le premier est un **plancher numérique**, et il est nouveau dans ce dépôt :
sous vingt jours, au strike soixante-dix, la correction du second ordre tombe
**au-dessous de la résolution d'un flottant double** — le prix corrigé est le
même nombre que le prix de départ, et la volatilité implicite qu'on en tire
est du bruit d'arrondi. Le premier jet traçait ce bruit, et la planche le
montrait comme une chute verticale. `tenor_inversible` publie désormais ce
ténor et un test exige que le raccourci soit mort en deçà ; le mois du
document, lui, est mille fois au-dessus du plancher. Le deuxième est **le
domaine déclaré après les tracés** — le piège de la partie XXII, retrouvé
identique : les trois courbes du prix contre la volatilité se dessinaient dans
le domaine par défaut et sortaient du cadre à mi-parcours, ce qu'aucun
balayage ne voit ; un test enveloppe maintenant `Panel.domain` et refuse tout
tracé posé avant elle. Le troisième est **une légende écrite devant un cadre
borné**, pour la septième fois : la grille du relief du volga s'arrêtait à 1,20
de moneyness quand la crête de six mois tombe à 1,28, si bien que le titre
annonçait une crête qui s'éloigne au-dessus d'une rampe monotone ; la grille
va maintenant à 1,45 et un test exige qu'elle encadre la crête à toutes les
échéances de la surface.

Sa **partie XXVII** ferme la série d'options par le guide des grecs du
troisième ordre — `ordres.py` + `figord.py`. C'est le seul des neuf dont la
dernière section écrive elle-même la conclusion que les huit autres laissent
croire l'inverse : *ces grandeurs décrivent comment votre exposition va
changer ; elles ne disent rien de la direction du prix.* Le dépôt ne la
conteste donc pas — il la chiffre, et il fait le contrôle qu'aucun des neuf
guides ne fait.

① **Le contrôle, et c'est la règle du dépôt appliquée à cinq objets neufs.**
Speed, Zomma et Ultima sont écrits à côté de la dérivée numérique de la
grandeur dont ils dérivent, et les colonnes se referment à toutes les
décimales publiées. La partie XXIV avait montré ce que coûte de ne pas le
faire : une dérivée croisée a vécu une partie entière ici avec un
dénominateur faux d'une racine, *parce que rien ne la consommait*.
② **Deux des cinq n'ont aucun paramètre libre.** À la monnaie le gamma vaut
une constante sur la racine de l'échéance et le véga cette constante fois la
racine, donc Color et Veta ne dépendent **ni de la volatilité, ni du niveau,
ni du taux** : `√(T/(T−Δt))` et `1 − √((T−Δt)/T)`, mesurés à quatre
décimales. Le guide dit « substantiellement plus de gamma demain » et « le
véga du mois avant se volatilise » ; les deux sont justes, et ce que la
mesure ajoute est qu'ils *se calculent sans rien savoir du marché*. La
lecture simple laisse deux termes, et **le portage domine partout** : la
question de la partie XXIII sur un cinquième objet.
③ **Le premier des neuf guides qui se surestime.** « Le dernier jour, le
gamma peut être divisé par deux sur une fraction de pour cent » : le
mouvement se résout et vaut `√(2 ln 2)·σ√T` — **la constante de la largeur
d'un niveau de gamma de la partie XIX**, retrouvée sur un objet sans rapport.
À un jour il faut 1,52 % du comptant, et le seuil n'est franchi que dans les
**10,3 dernières heures**. Les cinq guides qui précèdent se sous-estimaient.
④ **Ultima a exactement deux bascules, et cela se démontre.** Son facteur est
un trinôme du second degré en `d₁d₂`, de racines `(3 ± √(9+4σ²T))/2`. La
seconde borne la bande négative ; **la première n'est jamais atteinte**,
parce que `min(d₁d₂) = −σ²T/4` tombe au-dessus d'elle — et ce minimum est au
**forward**, pas à la monnaie (`e^{−(r−q)T}`). L'affirmation du guide se
démontre donc au lieu de se vérifier.
⑤ **Trois seuils, trois bandes emboîtées, et la première qui soit cotable.**
Le même produit borne le creux du volga (seuil zéro), la bande de Zomma
(seuil un) et celle d'Ultima (seuil trois) : 0,51 %, 14,3 % et 24,8 % du
comptant à trente jours, un facteur **48** entre les extrêmes. Les parties
XXII, XXIV et XXVI avaient chacune conclu que leur bande tombait sous le pas
d'une grille de strikes ; *celle d'Ultima le dépasse*. « Reflète la structure
du volga » est juste de la forme et faux de l'échelle, et l'échelle décide si
un objet existe sur un tableau de cotation.
⑥ **Les quatre-vingt-dix-neuf pour cent sont sous-estimés.** Sur 20 000
tirages joints, la part de variance que delta, gamma, thêta et véga
expliquent ne descend jamais sous **99,7 %** pour un livre nu ni **97,8 %**
pour un livre couvert en delta, et dans le cas que le guide décrit lui-même
le résidu vaut **0,9 millionième**. Le livre couvert, qu'il donne comme le
premier des trois cas où les termes supérieurs comptent, se dégrade
réellement et pas jusqu'à l'effondrement : *retirer le delta ne fait pas
apparaître les termes supérieurs, cela retire le terme qui les écrasait.* Et
la variable n'est pas celle qu'on croit — c'est la **durée de détention**,
pas la maturité.
⑦ **Le décompte** : trois affirmations déplacent le risque, deux l'horloge,
deux rien, **aucune la direction** — sixième partie consécutive. Sur les
**soixante-sept** affirmations des neuf parties d'options, aucune ne donne un
sens.

Trois pièges y sont enterrés, et deux n'ont été vus qu'en regardant la page.
Le premier est **une barre à baseline tronquée**, et le dépôt l'interdit : la
part expliquée vit entre 97,8 et 100 %, tracée en barres partant du bord
gauche du cadre elle donnait des longueurs proportionnelles à `part − 94 %`,
c'est-à-dire à rien. La planche publie maintenant des **haltères** — un point
par livre, un trait entre les deux — et le cadre de droite passe en échelle
logarithmique, la seule qui tienne trois ordres et demi de grandeur. Le
deuxième est **un axe linéaire sur une loi de puissance** : les deux courbes
de l'horloge s'effondraient contre le bord gauche, quatre-vingt-dix pour cent
du cadre vide et toute la forme dans une lisière de deux jours ; le balayage
d'occupation ne le voit pas, *le cadre est plein, c'est la donnée qui est
écrasée*. Le troisième est **un point posé sur la ligne de zéro** : la valeur
d'Ultima à la monnaie vaut 235 fois moins que son pic, donc son point tombait
exactement sur la ligne à côté des deux vraies bascules et la planche
montrait trois traversées là où il y en a deux.

Sa **partie XXVIII** est le dixième et dernier guide de la série d'options,
consacré à la volatilité implicite — `implicite.py` + `figiv.py`. C'est le
**second des dix à publier le résultat de son propre test négatif**, après
celui du vanna, et le seul dont ce résultat porte sur un outil qu'il
recommande par ailleurs : une relation monotone entre l'IV rank et les
résultats à venir, dit-il, *disparaît entièrement* dès que la fenêtre de
classement est rendue strictement glissante. Sa phrase d'ouverture est la
meilleure définition de la série — *l'implicite n'est pas une prévision, pas
une mesure ; c'est le nombre qu'il faut mettre dans le modèle pour retrouver
un prix déjà observé* — et le dépôt en tire ce qu'elle implique : si c'est un
changement d'unités, **la précision de la traduction se calcule**.

① **Deux bornes que le guide ne nomme pas.** Il borne l'existence de la
solution par l'arbitrage. Il en manque deux, plus proches : le lieu où un
seul tick vaut un point entier de volatilité (`100·tick/𝒱`, qui diverge où le
véga meurt — 0,44 point à la monnaie et à trente jours, 3,5 à cinq deltas et
une semaine), et surtout `moneyness_cotable`, **le lieu où le prix théorique
tombe sous un demi-tick** : l'écran affiche zéro, et zéro est *sous* le
plancher d'arbitrage. À sept jours cette frontière est à 7 % de la monnaie.
② **Un IV rank sur un an porte l'information de deux observations.** C'est le
résultat structurant, et il vient d'un fait absent du guide : la volatilité
est persistante, donc l'échantillon effectif d'une fenêtre vaut `n(1−ρ)/(1+ρ)`
= `κT/2` — *le nombre d'observations disparaît de la formule*. Contrôlé
contre la dispersion mesurée d'un percentile sur quatre cents fenêtres.
Conséquence : séparer un percentile de 80 d'un percentile de 50 demande
**8,8 ans**, et « annoncez la fenêtre » est juste et insuffisant, puisque la
fenêtre ne dit pas l'échantillon.
③ **Le rang est hostage d'un point, le percentile d'un sur n**, et le rapport
des deux sensibilités **croît avec la fenêtre** : allonger la fenêtre, geste
par lequel on croit stabiliser une statistique, aggrave le rang dans la
proportion où il améliore le percentile. C'est le défaut du Calmar de la
partie XVIII sur un troisième objet.
④ **Le look-ahead reproduit sous loi nulle**, et le premier jet s'y est
trompé — voir les pièges. À loi nulle correcte, le classement glissant rend
0,03 (sous son seuil) et le classement fuité 0,22, **et l'artefact grandit
avec l'horizon de détention**, ce qu'aucun des dix guides n'écrit.
⑤ **Une part de la prime publiée est une propriété de l'unité.** Un vendeur
dont l'implicite égale exactement la volatilité vraie a une espérance **nulle
en variance** et **positive en volatilité** : la racine est concave, le biais
vaut 0,23 point par expiration mensuelle — un neuvième du bas de la
fourchette que le guide annonce — et sa forme fermée `σ/(4h)` referme la
mesure. *Le guide écrit que l'option est cotée dans les mauvaises unités,
exprès ; voici ce que l'unité paie.* Et le vendeur sans le moindre avantage
gagne **53,9 %** de ses expirations, ce qui fait vivre la prime courte bien
au-delà de ce que son espérance justifie.
⑥ **Les cinq pièges, tous en points de volatilité**, et le classement n'est
pas celui de la liste : le plus cher est « grecs de fournisseur », que le
guide place en dernier, et il l'est *par construction* — il cache les quatre
autres à la fois. Deux d'entre eux sont **le même nombre**, `−Δ·ΔS/𝒱`.
⑦ **Le décompte** : cinq affirmations déplacent le risque, une l'horloge,
trois rien, **aucune la direction** — septième partie consécutive. Sur les
**soixante-seize** affirmations des dix parties d'options, aucune ne donne un
sens.

Quatre pièges y sont enterrés, et deux sont des affirmations écrites d'avance
que la mesure a réfutées. Le premier est **le signe d'une forme fermée** :
`∂σ/∂S` à prix constant vaut `−Δ/𝒱`, le premier jet écrivait le signe opposé,
et *les cinq pièges, tous pris en valeur absolue, ne voyaient rien* — c'est le
contrôle contre la réinversion complète qui a rendu deux cents pour cent
d'écart. **Une forme fermée dont on ne consomme que la valeur absolue est une
forme fermée à moitié contrôlée.** Le deuxième est **la loi nulle du
look-ahead**, qui n'en était pas une : le premier jet posait le gain comme le
niveau de volatilité moins la réalisée qui suit, et la colonne glissante
rendait 0,284 là où zéro était exigé — non par un bug, mais parce que *sous un
retour à la moyenne le niveau prédit vraiment la variation*, et que confondre
le niveau avec un prix est exactement la confusion que le guide dissout. Le
troisième est **le delta de la frontière** : on attendait une horizontale par
analogie avec le pic du vanna de la partie XXIV, la mesure rend une
décroissance d'un facteur dix, et le mécanisme est qu'un seuil *absolu* sur
une densité qui s'aplatit ne peut pas rendre un argument constant. Le
quatrième n'a été vu qu'en regardant la page : la surface du pas de cotation
était portée en **moneyness**, si bien qu'une de ses cellules — `S/K = 0,90`
à deux jours — rendait dix millions de points de volatilité par tick sur un
strike qui ne cote plus du tout ; elle est en **delta** depuis, pour la raison
même que le guide donne.

Sa **partie XXIX** poursuit la série d'options par le guide du skew —
`skew.py` + `figsk.py`. C'est le **troisième des onze à publier le résultat
de son propre test négatif**, après ceux du vanna et de l'implicite, et il
est le seul des trois à expliquer *pourquoi* ce résultat ne condamne pas
l'objet : le skew de put comme prédicteur n'a pas survécu — corrélation de
rang de −0,014 sur 495 séances — et *ce n'est pas une preuve que le skew ne
veut rien dire ; c'est une description du prix de la protection de queue,
maintenant, et on la vend comme une prévision constamment.* C'est la thèse
de la quatrième partie, formulée par un praticien qui n'avait aucune raison
de la formuler.

① **Un résultat négatif sans sa puissance ne dit presque rien.** Le seuil de
ce test vaut **0,088** sur 495 séances, et le guide ne le publie pas : le
nombre observé en est à 0,31 écart-type, donc le test ne rejette rien — et
*il n'aurait pas non plus détecté un effet de la taille qu'on cherche*.
Établir une corrélation de 0,05, qui serait considérable ici, demande 6,1
ans. La loi nulle est simulée (quatre mille tirages de deux séries
indépendantes, Spearman) et le seuil de Fisher contrôlé contre ses
quantiles. **Sans le seuil, « nous n'avons rien trouvé » et « nous ne
pouvions rien trouver » se lisent pareil.**
② **Les trois conventions ne mesurent pas le même objet.** Les strikes à
vingt-cinq deltas se tiennent à `d₁ = ±0,6745` — le quartile de la loi
normale, d'où le nom de la convention — donc le risk reversal sonde une
bande **proportionnelle à `σ√T`** quand la convention à moneyness fixe en
sonde une constante. Leur rapport passe de 0,47 à trente jours à 1,14 à un
an, et varie d'un facteur 3 sur la plage de volatilité **à peau
rigoureusement inchangée** : *la convention qu'on choisit pour être
insensible au comptant est la plus sensible à la volatilité, et un skew qui
« se raidit » peut n'être qu'une volatilité qui monte.*
③ **« Le skew s'aplatit avec le ténor » dépend de la convention**, et c'est
le résultat de la partie. Si la pente locale décroît en `T^{−H}`, le risk
reversal se comporte en `T^{1/2−H}` — sa bande s'élargit en `√T` pendant que
la pente s'aplatit. **Il ne décroît donc qu'au-delà de `H = 1/2`**, et à la
valeur que la littérature retient son exposant mesuré vaut −0,02, c'est-à-dire
plat. Le décalage entre les deux exposants vaut un demi en théorie, 0,48 à
la mesure, et **ne bouge pas d'un centième sur toute la grille du seul
paramètre libre** : c'est ce qui en fait un résultat et non un réglage.
*L'affirmation la plus consensuelle du document est vraie dans deux
conventions sur trois, et rien dans sa formulation ne dit lesquelles.*
④ **Le coût d'une erreur de régime, et le mot qui porte le sens.** Le guide
dit « plusieurs deltas sur chaque strike simultanément ». Exact par option —
1,54 point de delta à cinq pour cent sous la monnaie — et une option seule ne
coûte que **0,025 friction par séance** : c'est *simultanément* qui porte
tout, et il faut **39 contrats** sur le même strike pour en coûter une. La
correction porte le **véga** et non le vanna, résultat de la partie XXIV
importé et non recopié.
⑤ **Vendre du skew, c'est prendre une position directionnelle.** Le risk
reversal a un véga net **nul par parité** (le véga ne dépend de `d₁` que par
une fonction paire, les deux strikes ont des `d₁` opposés) et un delta net
qui vaut **exactement deux fois le delta de sa convention**, sans dépendance
à la peau, à l'échéance ni à la volatilité. Son seuil de rentabilité vaut
**0,10 pt/h**, soit 0,17 fois le plancher du domaine plausible : il passe
*sous* ce plancher, parce que la position n'a aucune barrière et achète la
séance entière. C'est le seuil le plus bas de tout le document, et ce n'est
pas une bonne nouvelle.
⑥ **Les trois forces, et laquelle est établissable.** Ce guide est le seul
des onze à donner une conséquence testable par mécanisme. Le dépôt n'a pas
de données et ne peut en tester aucune ; il chiffre ce qu'elles coûteraient,
et le classement est un renversement : le levier se voit en quelques
semaines, « la prime de risque de crash » — sur laquelle repose tout
l'argument économique du skew — demande **31 ans**, un facteur 975 entre les
deux bouts.
⑦ **Le décompte** : quatre affirmations déplacent le risque, une l'horloge,
quatre rien, **aucune la direction** — huitième partie consécutive. Sur les
**quatre-vingt-cinq** affirmations des onze parties d'options, aucune ne
donne un sens.

Cinq pièges y sont enterrés, et trois sont des affirmations écrites d'avance
que la mesure a réfutées. La **courbure de la peau** ne s'aplatissait pas
avec la pente dans le premier jet : à grand `H` elle dominait l'aile d'un an
et le décalage d'un demi — le résultat de la partie — s'y dégradait de
moitié. *Une surface où la pente s'aplatit et où la courbure reste ne décrit
aucun marché ; elle décrit un modèle qu'on a écrit sans le relire.* On avait
écrit que **le coût d'une erreur de régime dépassait la friction** : il vaut
deux centièmes par option, et c'est la taille de livre qu'il fallait
publier. On attendait le **sommet de la surface des régimes aux échéances
longues**, où le véga est le plus grand : l'arête de la monnaie est *plate*,
parce que le véga croît en `√T` exactement autant que la pente décroît, et
ce qui monte est l'aile. On attendait un **décalage indépendant de la
volatilité** : il se dégrade de 0,50 à 0,40, dans le sens que le mécanisme
prédit puisque le premier ordre suppose une bande étroite — *un écart qui va
dans le sens prédit est un contrôle, pas un défaut.* Et la forme fermée de
l'étendue à la monnaie portait **deux `σ` au lieu d'un**, rendant le quart du
nombre mesuré : le véga porte le comptant et la pente par point le porte au
dénominateur, donc il s'annule et il ne reste qu'une volatilité.

Sa **partie XXX** est la feuille de spéculation — `speculation.py` +
`figspec.py`. Les vingt-neuf parties qui précèdent décrivent ; celle-ci
décide. Chaque mesure du document y est convertie en la seule chose qu'un
opérateur ait à savoir avant d'entrer : si je prends position ici, dans un
sens ou dans l'autre, quelle probabilité, quel coût, et quelle dérive
faudrait-il. **Rien n'y est inventé** — la chaîne existait, il fallait la
brancher sur les deux sens. Et deux faits en sortent qui n'étaient nulle part.

① **Une position a trois fins, pas deux.** Le stop et l'objectif se
déclarent ; la sortie au marché parce que la séance se ferme, non. Elle vaut
zéro au stop déclaré et **28,5 %** au stop élargi.
② **`a/(a+b)` ne tient que tant que l'objectif reste dans la portée de la
séance**, et c'est la contrainte que la partie X n'avait pas relevée. Une
séance parcourt 24,7 points ; à un rapport d'un pour vingt, un stop de
0,150 % en demande **7,29 écarts-types**. La probabilité d'objectif n'y vaut
donc pas 4,76 % mais **zéro**, et le rapport que la séance autorise
réellement à cinq pour cent vaut **5,2 et non 20**. *Élargir le stop divise
le seuil par cinquante-trois — le résultat de la partie X, intact — et le même
geste rend l'objectif inatteignable si l'on garde le rapport : les deux
leviers ne se règlent pas séparément.*
③ **À dérive nulle les deux sens rendent le même nombre à la précision
machine**, et un test l'exige. Tout écart publié entre les deux sens est donc,
par construction, la dérive et rien d'autre — c'est une règle de lecture, et
la partie XV avait rencontré le défaut qu'elle interdit.
④ **L'écart directionnel passe par un maximum, et il se calcule** : 43,4
points de taux à **102 minutes**, contre 12,6 à cinq minutes et 18,2 sur la
séance entière. Le fait qui le rend publiable est qu'à cet horizon
**l'objectif vaut exactement un écart-type de séance** (1,02 mesuré) : la
seule échelle où la dérive dispose de toute la séance sans que la séance lui
reprenne l'objectif. La frontière est nommée — au-delà de la séance l'écart
remonte sans limite, donc l'optimum est celui d'un opérateur
intrajournalier.
⑤ **Le seuil a deux routes qui ne s'accordent pas.** Wald borné par la séance
donne 8,19 pt/h au stop déclaré ; le problème à deux barrières non borné,
3,75. Une affirmation écrite d'avance — le raccourci retournerait le verdict —
est **réfutée par la mesure** : les deux routes excluent la géométrie
déclarée partout. Ce qu'il change est l'ampleur, dix-sept pour cent au-dessus
du plafond au lieu d'un facteur 2,6. *Il ne retourne pas le verdict, il le
rend discutable, ce qui suffit à faire vivre une géométrie que la mesure
condamne.*
⑥ **Le catalogue relu comme des positions** rend 33,33 % exactement jusqu'à
quinze minutes puis décroche d'un facteur **7,3**. Les lectures longues ne
sont pas moins fiables : à rapport égal, elles sont innégociables dans une
séance.
⑦ **Le bandeau.** Chaque figure du document porte désormais sous sa légende ce
qu'une position y coûterait dans les deux sens, recalculé à la construction
par `pieds.figure_html` — le seul point d'entrée commun aux documents. Les
deux autres builds ne le passent pas et sont rendus comme avant.
⑧ **Aucune géométrie ne passe les deux conditions.** La déclarée échoue sur la
dérive, les deux élargies sur la portée. Le réglage que la partie propose —
102 min, stop 12,66 pt, un pour deux — *ne promet aucun avantage* : il dit où
une dérive, si elle existait, serait la plus vite prouvée ou réfutée.

Deux pièges y sont enterrés. Le premier ne se serait **jamais signalé** : la
table de préfixes qui associe une figure à sa famille avait été *devinée* et
non relevée sur les clés réelles, et trente-sept figures sur deux cent
quatorze n'accrochaient aucune famille — les treize du delta, les neuf du
flux, les sept couches du catalogue, les cinq de la robustesse. Le bandeau se
serait tu, et une planche muette ressemble à une planche sans objet
directionnel. Un test lit maintenant toutes les clés du gabarit et refuse la
moindre orpheline. Le second est **une barre sans unité commune** : la
première planche du décompte alignait horizon, stop, objectif et rapport sur
un même axe en pour cent, chacun divisé par un dénominateur choisi à la
main — de la décoration, que le dépôt interdit. Elle publie maintenant
l'écart directionnel en points de taux, une seule unité, où le réglage
proposé rend 43,4 contre 4,4 au mieux des trois géométries déclarées. Une
troisième planche alignait dix-neuf barres anonymes ; elle en publie six,
nommées, et le regroupement est calculé.
