# Zones gamma, IV et profil de volume — format ALPZ 1 et indicateur Alp-0 Zones

Note d'outillage, comme `docs/gex-discord-vers-tradingview.md` : elle ne
mesure rien et ne porte aucune loi nulle. L'indicateur est `pine/alp0-zones.pine`
(Pine Script v6). Il **reporte** des niveaux, **détecte** leurs touches et
**compte** les réactions. Il ne passe aucun ordre, n'affiche aucune
probabilité, et un comptage de rejets n'est pas une rentabilité après coûts.

Ce document fixe l'**étape 1** du cahier des charges : import texte, niveaux,
regroupement lisible, touches. L'indicateur porte aussi, en tête, la heatmap
z-score des bougies (l'ancien « Z + Single Prints (OPEX) », corrigé — §1 bis). Le profil GEX signé 0DTE à droite du prix
(début de l'étape 2) y est déjà, parce qu'il ne demande aucune donnée de plus
que le format. Restent pour la suite : la comparaison minuit / 5 h, les
extrémités de structure, les confirmations et les statistiques de confluence
(étape 3).

---

## 1. Installer l'indicateur

1. Ouvrir l'éditeur Pine de TradingView (version web ou bureau ; si
   l'application mobile ne propose pas l'éditeur, passer par tradingview.com
   dans un navigateur).
2. *Nouveau script* → *Indicateur*, tout effacer, coller le contenu entier de
   `pine/alp0-zones.pine`, *Enregistrer* sous le nom « Alp-0 Zones », puis
   *Ajouter au graphique*.
3. Ouvrir les réglages de l'indicateur → *Paramètres en entrée* → groupe
   **⑤ Relevés Gexbot** : coller le texte de Lou dans **Zone A**. Les zones B et
   C servent à l'historique (chaque zone accepte 40 960 caractères au plus,
   limite documentée de Pine pour un texte).
4. Graphique conseillé : **NQ1!** ou **MNQ1!** en **1 minute**. Les touches et
   la fenêtre de 60 minutes n'ont de sens que sur une unité de temps qui divise
   60 minutes ; au-delà de 5 minutes, la plupart des issues deviennent
   ambiguës par construction.
5. Si TradingView signale une erreur à l'enregistrement, copier le message
   exact (ligne et texte) : il n'y a pas de compilateur Pine joignable depuis
   le dépôt, et c'est la seule vérification que les essais ci-dessous ne font
   pas.

Le groupe **④ VWAP SELECTION** reprend un par un les réglages de « The
Strategists - Aggregated VWAP » tels qu'ils sont saisis sur le graphique :
ancrage *Day*, source hlc3, six multiplicateurs (1, 2, 3, 0.5, 1.5, 2.5) avec
leur case, *Plot Standard Deviation*, *Fill Bands*, VWAP de la période
précédente avec ±1 et ±2, *Fill Previous Bands*, étiquettes en bout de bande
(*Label offset* 1). L'écart-type est l'écart-type **pondéré par le volume**
depuis l'ancrage, `σ² = Σ(v·P²)/Σv − VWAP²`, la forme du VWAP intégré. Deux
réglages de l'original ne sont pas repris : l'**agrégation multi-places**
(propre au bitcoin, sans objet sur un future qui ne cote qu'au CME) et
l'affichage des VWAP par symbole agrégé.

---

## 1 bis. La heatmap z-score — ce qui a été corrigé

Groupes **① Z-Score**, **② Z-Score Colors**, **③ Z-Score Brightness**. Le calcul
est celui du script d'origine : `z = (ohlc4 − SMA50) / σ50` (σ par division
par N, comme `ta.stdev`), corps neutre sous T1 = 2, dégradé cyan → magenta de
T1 à T2 = 3, magenta au-delà ; c'est la valeur **absolue** du z-score qui est
lue. Ce qui a changé :

| avant | après |
|---|---|
| nommé « Z + Single Prints (OPEX) », sans aucun calcul de single prints ni d'OPEX | rangé sous son vrai nom, en tête d'Alp-0 Zones |
| série « ΓΣZera Heatmap » : titre corrompu à l'encodage | « Z-Score Heatmap » |
| z = 0 tant que les 50 bougies ne sont pas réunies, et sur un prix immobile | z = na : bougie neutre, « n/a » dans la fenêtre de données — un zéro aurait été une valeur fabriquée |
| l'éclaircissement des mèches et bordures remettait la transparence à zéro | transparence conservée |
| libellés « Cyan (2σ) » / « Magenta (3σ) » figés quel que soit le seuil, variables `c_neg` / `c_pos` qui désignaient deux intensités et non deux signes | « Cyan (T1) » / « Magenta (T2) », variables nommées d'après ce qu'elles sont |
| T2 ≤ T1 : dégradé dégénéré | tout ce qui dépasse T1 prend la couleur de T2 |
| `max_bars_back = 5000`, quotas de lignes et d'étiquettes inutilisés | retirés |

La bougie en cours change de couleur jusqu'à sa clôture, comme le prix
qu'elle porte : ce n'est pas un repaint de l'historique, mais la couleur n'est
définitive qu'à la clôture. Une fois Alp-0 Zones installé, l'ancien indicateur
« Z + Single Prints (OPEX) » peut être retiré du graphique : sinon deux jeux de
bougies colorées se superposent.

---

## 2. Le format ALPZ 1 — ce que Lou remplit

Un texte, ligne par ligne. La **première ligne utile** est l'en-tête de
version :

```
ALPZ 1
```

Les lignes vides et celles qui commencent par `#` sont ignorées. Les mots
sont séparés par des espaces. Chaque ligne commence par une lettre qui dit ce
qu'elle porte :

| ligne | rôle | forme |
|---|---|---|
| `R` | ouvre un **relevé** (un instantané) | `R clé=valeur clé=valeur …` |
| `B` | **base** de conversion du relevé en cours | `B base=… fut=… idx=…` |
| `N` | un **niveau** du relevé en cours | `N CODE PRIX [nom source libre]` |
| `G` | métadonnées du GEX par strike | `G unite=… signe=… origine=… [net=…]` |
| `S` | GEX **signé** par strike | `S STRIKE:GEX STRIKE:GEX …` |

Un relevé va de sa ligne `R` à la ligne `R` suivante. Un relevé publié **ne se
modifie plus** : s'il était faux, on en ajoute un autre avec un nouvel `id`.

### 2.1 La ligne R

| clé | obligatoire | valeur | exemple |
|---|---|---|---|
| `id` | oui | identifiant unique, sans espace | `NQ-1106-G0` |
| `src` | oui | source | `GEXBOT`, `TV` ; **`FICTIF`** pour un exemple |
| `fam` | oui | famille : `GEX`, `IV` ou `VP` | `GEX` |
| `cmd` | non | commande exacte, sans espace | `/gex` |
| `inst` | oui | instrument dans lequel les prix sont écrits | `NDX`, `NQ`, `MNQ` |
| `cible` | oui | contrat(s) où tracer, séparés par des virgules | `NQ`, `MNQ`, `NQ,MNQ` |
| `contrat` | non | échéance du future visé | `NQZ2026` |
| `date` | oui | date des données (séance d'options d'où elles viennent) | `2026-11-05` |
| `collecte` | oui | heure où Lou a lancé la commande, heure de Paris | `2026-11-06T00:00` |
| `dispo` | oui | heure où le texte est collé dans TradingView | `2026-11-06T00:04` |
| `dte` | GEX, IV | DTE **demandé**, `début-fin` | `0-0`, `1-1` |
| `ech` | GEX, IV | échéance(s) **réellement retournée(s)**, virgules | `2026-11-06` |
| `seance` | VP | séance que décrit le profil (complète, antérieure) | `2026-11-05` |

Dates `AAAA-MM-JJ`, heures `AAAA-MM-JJTHH:MM` (secondes facultatives
`:SS`), toujours en heure de Paris : les changements d'heure sont appliqués
automatiquement. Une heure qui n'existe pas (02:30 le dernier dimanche de
mars) ou qui existe deux fois (02:30 le dernier dimanche d'octobre) est
**refusée** : il n'y a pas de bonne façon de la deviner.

Le **DTE réel** est recalculé à partir de l'échéance retournée, en jours
ouvrés (lundi-vendredi ; les fériés ne sont pas connus du script) depuis le
jour de séance — le jour du gel. C'est lui qui fait foi et qui s'affiche
(`0D`, `1D`, `10D`), jamais le DTE demandé.

### 2.2 La ligne B — conversion NDX → NQ

Obligatoire quand `inst` est `NDX` et que le graphique est NQ ou MNQ :

```
B base=118.50 fut=NQZ2026:29218.50@2026-11-05T22:00 idx=NDX:29100.00@2026-11-05T22:00
```

`prix tracé = prix source + base`. `fut` et `idx` sont les deux prix qui ont
servi au calcul, avec leur heure. Le script vérifie `base = fut − idx` (à un
centième près, sinon le relevé est refusé) et déclare la base
**APPROXIMATIVE** quand les deux heures s'écartent de plus de 60 secondes
(réglable), quand l'un des deux prix manque, ou quand l'échéance de `fut`
n'est pas celle du graphique (roll). Rien n'est converti sans base : un
relevé NDX sans ligne B n'est pas tracé.

L'indice NDX ne cote qu'en séance (9:30-16:00 à New York). À minuit à Paris,
le dernier cours de l'indice est celui de 16:00 : une base mesurée avec le NQ
de minuit soustrairait deux instants différents. La base synchrone est donc
celle de **22:00 à Paris (16:00 à New York)**, la veille, comme dans
l'exemple.

Entre NQ et MNQ de même échéance, la base est nulle par convention (même
indice, même règlement final) ; le tableau le dit.

### 2.3 Les lignes N — codes et familles

`N CODE PRIX [nom source]`. Le prix s'écrit avec des chiffres et un point
décimal, **sans séparateur de milliers** : `29250.5`. `29,250` ou `29 250`
sont refusés plutôt que lus de travers. Le nom source (le texte du robot) est
gardé tel quel et apparaît dans le détail.

| famille | codes | uniques par relevé |
|---|---|---|
| `GEX` — positionnement options | `CW` call wall · `PS` put support · `GF` gamma flip · `R1` `R2` `S1` `S2` · `MaxPain` (ou `MP`) | tous |
| `IV` — volatilité implicite | `IV+1σ` `IV-1σ` `IV+2σ` `IV-2σ` (σ peut s'écrire `s` ou s'omettre : `IV+1`) · `IV-C` · `IV-P` · `IVgb` | tous |
| `VP` — profil de volume | `POC` `VAH` `VAL` · `HVN` `LVN` | tous sauf `HVN`, `LVN` |

Le sens de `IV-C`, `IV-P` et `IVgb` est celui de la source : le script ne
l'interprète pas. Un code doit appartenir à la famille du relevé (`POC` dans
un relevé `GEX` est refusé). Un code unique donné deux fois avec deux prix
est un **conflit** : les deux sont écartés et signalés.

Niveaux **secondaires** (masqués par défaut, listés au tableau) : `S2`, `R2`,
`LVN`, `IV+2σ`, `IV-2σ` — liste réglable.

### 2.4 Les lignes G et S — GEX signé par strike (facultatif)

```
G unite=Mds$ signe=calls+/puts- origine=api net=0.85
S 29150:0.80 29200:0.95 29250:1.60
```

`unite` et `signe` sont obligatoires dès qu'il y a une ligne `S` : sans eux,
le profil est indisponible. `origine` vaut `api` (valeurs numériques
exportées) ou `image` (relues sur la carte du robot : le profil est alors
déclaré **approximatif**). `net` est le GEX net donné par la source ; c'est
la seule chose dont le script tire un régime positif ou négatif — jamais de
la position du prix par rapport au gamma flip. Les strikes s'écrivent dans
l'échelle de `inst`, la base de la ligne B les convertit.

### 2.5 Les règles que le script applique au texte

- **Doublon d'échéance** : deux relevés de même famille, même cible, même
  créneau et **même échéance réelle** ne comptent qu'une fois. On garde celui
  dont le DTE demandé contient le DTE réel. Cas typique : `0-0` et `1-1`
  demandés hors séance rendent la même échéance.
- **Plage cumulative** : `dte=0-10` additionne des échéances. Si elle recouvre
  une échéance déjà fournie au même créneau, elle est écartée (option pour la
  garder, marquée non indépendante).
- **Instantanés séparés** : un relevé de minuit et un relevé de 5 h ne se
  remplacent jamais et ne fusionnent jamais dans une même zone.
- **Plausibilité** : à l'activation, un niveau à plus de 5 % du prix
  (réglable) est écarté et signalé — presque toujours une faute de frappe ou
  une base oubliée.
- **Aucune valeur fabriquée** : une donnée absente reste absente, une donnée
  invalide est refusée, et chaque refus est écrit au tableau avec sa ligne
  (`A:12` = zone A, ligne 12).

---

## 3. EXEMPLE FICTIF

Toutes les valeurs ci-dessous sont **inventées** pour montrer le format.
`src=FICTIF` fait afficher « ⚠ EXEMPLE FICTIF » en tête du tableau et
préfixer chaque étiquette de « FICTIF ».

<!-- EXEMPLE FICTIF : début -->
```
ALPZ 1
# EXEMPLE FICTIF — valeurs inventées pour montrer le format. Ne pas trader.
#
# 1. /gex NDX start_dte 0 end_dte 0, collecté à minuit pour NQ.
R id=NQ-1106-G0 src=FICTIF fam=GEX cmd=/gex inst=NDX cible=NQ contrat=NQZ2026 date=2026-11-05 collecte=2026-11-06T00:00 dispo=2026-11-06T00:04 dte=0-0 ech=2026-11-06
B base=118.50 fut=NQZ2026:29218.50@2026-11-05T22:00 idx=NDX:29100.00@2026-11-05T22:00
N CW 29350 Call Wall
N PS 28900 Put Support
N GF 29050 Gamma Flip
N R1 29175 Resistance 1
N S1 28975 Support 1
N S2 28925 Support 2
G unite=Mds$ signe=calls+/puts- origine=api net=0.85
S 28850:-0.40 28900:-1.10 28950:-0.65 29000:-0.30 29050:0.15
S 29100:0.55 29150:0.80 29200:0.95 29250:0.70 29300:0.45 29350:1.60
#
# 2. /gex NDX start_dte 1 end_dte 1 : l'échéance RÉELLE est le lundi.
R id=NQ-1106-G1 src=FICTIF fam=GEX cmd=/gex inst=NDX cible=NQ contrat=NQZ2026 date=2026-11-05 collecte=2026-11-06T00:01 dispo=2026-11-06T00:04 dte=1-1 ech=2026-11-09
B base=118.50 fut=NQZ2026:29218.50@2026-11-05T22:00 idx=NDX:29100.00@2026-11-05T22:00
N CW 29354 Call Wall
N PS 28850 Put Support
#
# 3. /iv NDX (Gexbot range NQ sous NDX), même créneau.
R id=NQ-1106-IV src=FICTIF fam=IV cmd=/iv inst=NDX cible=NQ contrat=NQZ2026 date=2026-11-05 collecte=2026-11-06T00:02 dispo=2026-11-06T00:04 dte=0-0 ech=2026-11-06
B base=118.50 fut=NQZ2026:29218.50@2026-11-05T22:00 idx=NDX:29100.00@2026-11-05T22:00
N IV+1 29420
N IV-1 28780
N IV+2 29630
N IV-2 28570
#
# 4. Profil de volume de la séance du 5, relevé à minuit pour NQ et MNQ.
R id=VP-1105 src=FICTIF fam=VP cmd=TV-VP inst=NQ cible=NQ,MNQ date=2026-11-05 collecte=2026-11-06T00:00 dispo=2026-11-06T00:03 seance=2026-11-05
N POC 29296
N VAH 29474
N VAL 29040
N HVN 29476
N LVN 29110
#
# 5. /gex NDX 0/0 relevé à 5 h pour MNQ : un instantané SÉPARÉ.
R id=MNQ-1106-G0 src=FICTIF fam=GEX cmd=/gex inst=NDX cible=MNQ contrat=MNQZ2026 date=2026-11-05 collecte=2026-11-06T05:00 dispo=2026-11-06T05:03 dte=0-0 ech=2026-11-06
B base=118.50 fut=NQZ2026:29218.50@2026-11-05T22:00 idx=NDX:29100.00@2026-11-05T22:00
N CW 29350 Call Wall
N PS 28900 Put Support
N GF 29060 Gamma Flip
```
<!-- EXEMPLE FICTIF : fin -->

Sur NQ1!, cet exemple trace les relevés 1 à 4 (créneau de minuit) ; sur
MNQ1!, les relevés 4 et 5 (créneau de 5 h, et le profil de volume commun). Le
CW 0DTE (29 350 + 118,50 = 29 468,50), le CW 1DTE (29 472,50), la VAH
(29 474) et le HVN (29 476) tombent à moins de 8 points les uns des autres :
ils forment **une** zone, étiquetée `CW 0D · 1D · VAH · HVN`, qui va de
29 468,50 à 29 476 — chaque prix reste exactement où la source l'a mis.

---

## 4. Ce que l'indicateur fait des relevés

**Activation.** Un relevé est actif sur les bougies qui **ouvrent** à partir de
sa disponibilité. Avant, il n'existe pas : ni tracé, ni touche, ni armement.
C'est la garantie d'absence d'anticipation.

**Gel à 22 h.** Pendant la journée, les niveaux s'étendent à l'infini vers la
droite. Au premier gel postérieur à la disponibilité (22:00 à Paris,
réglable), ils deviennent des segments. La fin du segment est **posée à
22:00 exactement**, mais Pine ne s'exécute qu'aux mises à jour du graphique :
le changement n'est **appliqué** qu'à la première bougie qui suit. Pendant les
semaines où Paris et New York ne changent pas d'heure le même dimanche, la
pause du CME tombe de 22 h à 23 h à Paris : aucune bougie à 22 h, le gel est
appliqué à 23 h, et le segment s'arrête quand même à 22 h.

**Confluences.** Les niveaux actifs sont triés par prix ; un niveau rejoint la
zone en cours si son écart au précédent est ≤ 8 points (réglable) **et** si
le diamètre de la zone reste ≤ 16 points (réglable — c'est ce qui empêche un
enchaînement de niveaux espacés de 7 points de couvrir 50 points). La zone
va du plus bas au plus haut de ses membres ; aucun prix n'est déplacé. Le mot
est CONFLUENCE : la proximité de deux niveaux n'est pas un test économétrique
de co-intégration, et le script ne suppose pas qu'une zone plus fournie soit
plus solide — les expositions de deux échéances voisines sont corrélées.

**Touche.** La bande d'une zone est `[plus bas − tolérance, plus haut +
tolérance]`, tolérance en ticks (4 par défaut, soit 1 point sur NQ). Une
touche est l'intersection d'une bougie confirmée avec la bande, quand la zone
est **armée**. Une zone s'arme quand une bougie entière est hors de la bande
et que 15 minutes (réglable) se sont écoulées depuis sa dernière touche : une
seule touche par excursion.

**Sens.** Le côté d'approche est celui de la dernière bougie entièrement hors
bande avant la touche ; si la bougie de touche **ouvre** hors de la bande,
c'est le côté de son ouverture. Venu d'en haut : test de **support**, la
réaction attendue est une hausse. Venu d'en bas : test de **résistance**,
réaction attendue à la baisse.

**Issue.** Seuils mesurés depuis les bords de la zone (sans la tolérance) :
réaction de **30 points** au-delà du bord proche, dépassement adverse de
**20 points** au-delà du bord opposé, fenêtre de **60 minutes** depuis
l'ouverture de la bougie de touche (tous réglables).

| état | règle |
|---|---|
| non touchée | aucune touche depuis l'activation |
| touchée → en observation | touche confirmée, aucun seuil encore atteint |
| rejetée | réaction atteinte avant l'adverse |
| cassée | adverse atteint avant la réaction |
| ambiguë | les deux seuils dans la même bougie — l'ordre intra-bougie n'est pas connu, il n'est pas inventé |
| non résolue | ni l'un ni l'autre dans la fenêtre |

La bougie de touche demande un soin de plus : ce qu'elle contient **avant** la
touche n'est pas une réaction. L'adverse y est toujours postérieur à la touche
(il faut traverser la zone pour l'atteindre). La réaction n'y est certaine que
si la **clôture** est au-delà du seuil ; un plus haut au-delà et une clôture en
deçà donnent « ambiguë » — le plus haut a pu précéder la touche.

**Sans repaint.** Toute la logique s'exécute sur bougie confirmée
(`barstate.isconfirmed`) : un état ne change qu'à la clôture et ne change
plus ensuite. Les essais le vérifient en rejouant la même séance tronquée.

**Profil 0DTE à droite.** Le relevé GEX disponible le plus récent dont
l'échéance **réelle** est le jour même, s'il porte des valeurs par strike.
Une barre horizontale par strike, à son prix exact converti, entièrement à
droite du prix (30 barres par défaut) ; négatif à gauche d'un axe vertical,
positif à droite, longueur proportionnelle à |GEX|. L'en-tête rappelle
source, échéance, heure du relevé, unité, convention de signe, régime **si
la source donne le net**, et que l'instantané est figé : ce n'est pas un flux
gamma en direct. Le profil n'est **jamais reconstruit** à partir de
CW/PS/GF : sans valeurs par strike, il est indisponible et le tableau dit
pourquoi.

**Tableau.** Relevés lus / actifs / à venir / écartés ; zones et confluences ;
comptes de touches par issue, zones simples et confluences séparées ; profil ;
base et sa qualité ; secondaires masqués ; quotas ; avertissements.
**Ce sont des comptes, pas une performance.** La comparaison simple /
confluence, l'incertitude, la référence comparable et la validation hors
échantillon sont l'objet de l'étape 3.

---

## 5. Ce que Gexbot renvoie, et ce que cela change pour Lou

Lu dans la documentation publique de Gexbot (docs.gexbot.com, novembre 2026) :

- `start_dte` et `end_dte` sont **inclusifs**, et une fenêtre de plusieurs
  échéances les **additionne** (`expiry_agg`). Une plage `0-10` est donc
  cumulative — d'où la règle du §2.5.
- « Une fenêtre sans échéance n'échoue pas : le robot passe à la première
  échéance à partir de `start_dte`, et le dit sur la carte. » Le DTE demandé
  ne dit donc pas l'échéance obtenue : **Lou recopie l'échéance écrite sur la
  carte** dans `ech`.
- Les contrats expirés sortent à leur heure d'expiration (16:00 à New York
  pour les quotidiennes) ; hors séance, rien n'est recalculé entre la clôture
  et la mise à jour d'avant-ouverture, et le week-end renvoie le cliché de la
  dernière séance. Conséquence directe pour le plan de test : **à minuit comme
  à 5 h à Paris, `0-0` et `1-1` peuvent renvoyer la même échéance**, et les
  deux créneaux peuvent porter les mêmes données. Le script le détecte (doublon
  d'échéance) au lieu de compter deux fois.
- `NQ` est un alias de `NDX` : `/iv NQ` interroge la chaîne d'options de
  l'indice. Lou écrit donc `inst=NDX`, et la ligne B convertit.
- Le robot Discord répond par des **cartes image** ; les valeurs par strike
  ne sont exportées en nombres que par l'API Research (`format=csv`), qui
  demande une clé. Sans elle, des valeurs relues à l'œil sont des estimations :
  `origine=image`, profil marqué approximatif.
- Unités : les indices (NDX) sont exprimés en milliards de dollars ; dans la
  version classique, le GEX des calls est compté positif et celui des puts
  négatif. C'est ce que `signe=calls+/puts-` consigne.

---

## 6. Limites — dites plutôt que simulées

- **Pas de réseau.** Pine ne lit pas Discord, ne lance aucune commande, ne
  joint aucune API. Le collage de Lou est la seule entrée.
- **Pas de mémoire propre.** Le texte collé *est* l'archive : le script ne
  peut ni reconstruire un relevé absent, ni écrire dans ses propres
  paramètres pour archiver de nouvelles données. Modifier un ancien relevé
  réécrit l'historique sans que rien ne le signale : garder une copie de
  chaque texte du jour.
- **Recalcul.** Tout changement de réglage ou de texte recalcule l'historique
  entier, y compris les comptes de touches.
- **Quotas.** 500 lignes, 500 étiquettes, 500 boîtes par script (limites
  documentées). Au-delà, TradingView effacerait les plus anciennes sans
  prévenir ; le script s'arrête avant (470) et le dit, en sacrifiant les
  jours les plus anciens, jamais le jour courant. Réduire « Jours affichés ».
- **Texte.** 40 960 caractères par zone ; une boucle Pine est limitée à
  500 ms par bougie, ce qui borne la taille utile d'un collage géant.
- **Export.** TradingView n'offre pas d'export CSV natif des dessins d'un
  script ; les comptes se lisent au tableau. Un export par séries tracées est
  envisageable à l'étape 3, à vérifier sur le compte de l'utilisateur avant
  d'être promis.
- **Alertes.** Facultatives, désactivées par défaut ; elles n'émettent qu'en
  temps réel, sur bougie confirmée.

---

## 7. Les essais

`tools/zones-pinets/` exécute **le vrai fichier** `pine/alp0-zones.pine` sous
PineTS (runtime Pine v6 libre de LuxAlgo) sur des séances synthétiques, et lit
ce qu'il dessine (lignes, étiquettes, boîtes, tableau). Chaque issue attendue
est calculée à la main avant l'exécution.

```
cd tools/zones-pinets && npm install && node scenarios.mjs
```

Couverture : touches et issues (rejet, cassure, ambiguë dans la bougie de
touche et dans la suivante, réaction douteuse, non résolue, une touche par
excursion) ; confluences (étiquette, diamètre borné, prix non déplacés,
secondaires) ; saisie invalide et données absentes ; doublons et plages
cumulatives ; quotas ; changements d'heure (heure inexistante, ambiguë, gel
en heure d'été, d'hiver et en semaine décalée) ; absence d'anticipation et de
repaint ; gel à 22 h ; créneaux NQ / MNQ ; profil 0DTE ; VWAP et bandes ;
l'exemple fictif ci-dessus ; z-score (valeur exacte contre une référence
indépendante, préchauffage en na, marche isolée à z = 7, dégradé, mèches et
bordures, T2 ≤ T1). 107 contrôles.

Ce que ces essais **ne prouvent pas** : PineTS n'est pas le compilateur de
TradingView. Il ne vérifie ni toutes les règles de typage (qualificatifs
*simple* / *series*), ni les avertissements de l'éditeur. Deux écarts de
PineTS ont été contournés dans le code, sans effet pour TradingView : une
fonction d'une seule expression qui lit un tableau global, et la comparaison
d'un booléen à une comparaison entre parenthèses. Et PineTS, faute de session
d'échange sur des bougies fournies, remet le VWAP « Day » à zéro à minuit UTC ;
sur NQ1!, TradingView le remet à l'ouverture de la séance CME.
