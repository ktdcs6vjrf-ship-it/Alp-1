# ALP-1 — mémoire de projet

Ce fichier existe pour qu'une session repartie de zéro retrouve l'état du
travail sans le redécouvrir. Le dépôt est la seule mémoire : ce qui n'est pas
écrit ici ou commité n'existe plus.

## Ce qu'est ce dépôt

Un papier de recherche en français, de forme SSRN, sur l'invariance des
géométries de sortie en intraday indice. Le noyau est un ensemble de modules
Python qui **calculent** les chiffres, et le document HTML est **construit**
à partir d'eux. Aucun nombre n'est écrit à la main dans le document.

Livrable principal : `docs/temps-de-marche-et-peremption.html`
(≈1,00 Mo — 49 sections en neuf parties, 107 tables, 48 figures).
Il est publié comme artefact : https://claude.ai/code/artifact/1a195a2a-36ad-47df-9d1d-e44c43b4f982

Second livrable : `docs/prouver-un-jugement.html` — **ALP nº 3**, sur
l'évaluation d'un opérateur discrétionnaire dont l'avantage n'est pas codable
(≈590 ko — 34 sections en dix parties, 8 tables, 20 figures dont deux
surfaces isométriques). Chaîne propre : `journal.py` → `operator.py` →
`attribution.py` → `report10.py` + `figdisc.py` → `discpaper.py`. Les sept
figures de couches sont reprises de `figterm.py` sans être redéfinies : elles
ne portent aucune couleur et adoptent seules le jeu de jetons sombre.

## Règles du dépôt — à ne pas enfreindre

1. **Stdlib uniquement.** Pas de numpy, pas de scipy, pas de pandas.
   Python 3.11+. Tout aléa est déterministe et amorcé par une graine explicite.
2. **Les figures n'écrivent aucune couleur en dur.** Elles passent par les
   jetons CSS de `alp1/figcss.py`. `tests/test_figures_all.py` balaie les dix
   modules `fig*.py` et refuse tout `#rrggbb` — y compris les entités HTML de
   la forme `&#8202;`, qui doivent être écrites en caractère littéral.
3. **Les comptes annoncés sont gardés par les tests.** `tests/test_docs.py`
   vérifie que le README dit vrai (nombre de tests, de parties) et
   `tests/test_workingpaper.py` vérifie la structure du document (sections,
   parties, tables, figures). Changer l'un impose de changer l'autre.
4. **Le document se reconstruit, il ne s'édite pas.** On modifie
   `docs/*.template.html`, puis `python main.py --wp`. Éditer le HTML construit
   à la main le remettrait en désaccord avec sa source au prochain build.
5. **Toute méthode nouvelle vient avec sa loi nulle.** C'est la méthodologie
   centrale du dépôt : un motif ne vaut que comparé à sa fréquence sous un prix
   sans dérive. Un estimateur qu'on ne sait pas calibrer contre son bruit ne
   rentre pas.

## Le résultat structurant

Sous un prix sans dérive, l'espérance nette par trade vaut exactement `−c/L`,
quels que soient le placement des barrières et la règle de gestion du stop.
C'est le théorème d'arrêt optionnel : `E[R] = µ·E[τ] − c`. Aucune géométrie ne
crée d'espérance ; elle ne fait qu'acheter du temps de marché `E[τ]`.

Corollaire mesuré partout dans le papier : **le bruit propre de chaque
instrument de mesure dépasse l'avantage que la stratégie exige.** Trois routes
indépendantes convergent sur le même mur — test t : 17 434 trades ; seuil
déflaté : 1 993 ; test G informationnel : 10 568.

## Carte des modules

- `measure.py` — chaîne de mesure, `scan_session`, paramètre `fill`
  (`"stop"` optimiste / `"extreme"` pire cas compatible avec la barre),
  `bounds()` qui encadre la mesure entre les deux.
- `strategy.py` — **la stratégie backtestable scellée** (618 lignes).
  Entrée minute 120, sortie 388, 3 tentatives. Sept portes de confluence
  déclarées (`band`, `localvol`, `dow`, `vwapband`, `ote`, `gamma`, `book`),
  toutes fermées dans `SEALED`. `validate()` fait tourner la batterie de sept
  contrôles ; un seul manqué refuse.
- `varratio.py` — ratio de variance de Lo–MacKinlay et loi d'échelle, avec
  sa loi nulle simulée. Attention : biaisé à Ĥ = 0,52 sur une vraie martingale.
- `entropy.py` — le plafond informationnel. `required_bits` (divergence de
  Kullback-Leibler), `trades_for_information` (non-centralité du test G),
  correction de biais de Miller–Madow.
- `nonlinear.py` — entropie de permutation (Bandt–Pompe) et DFA (Peng),
  chacune avec sa loi nulle.
- `discipline.py` — la déviation comme multiplicité : `k` écarts
  discrétionnaires valent `2^k` configurations effectives.
- `overfit.py` — purge, embargo, CSCV/PBO, bootstrap stationnaire.
- `report*.py` — chaque module fournit `values()` et `all_tables()` au
  document. `report9.py` est celui de la stratégie.
- `fig*.py` — dix modules de figures, chacun expose `render_all()`. `figdisc.py`
  est celui d ALP nº 3 et suit un jeu de jetons « terminal » qui lui est propre.
- `workingpaper.py` — fusionne valeurs, tables et figures, et construit le
  document. Toute collision de clé lève une erreur.

Hors du noyau Python :

- `pine/alp0.pine` — **Alp-0**, indicateur TradingView (Pine v6) écrit pour
  l'opérateur. VWAP ancré et bandes d'écart-type pondérées par le volume
  (0,5 à 3 σ), zones d'accumulation retenues seulement si volume **et**
  réaction tiennent, et signal de confluence quand une bande tombe sur une
  zone. Signal calculé sur barre fermée, donc sans repeinture. Ce fichier ne
  participe ni au document ni aux tests : il n'a pas de loi nulle et n'en
  revendique aucune — c'est un outil de lecture, pas une mesure.

## Le point qui décide la conception de la stratégie

Chaque porte de confluence ouverte **double** la famille de stratégies, donc
la taxe de sélection déflatée. Sur 7 012 trades, contre un Sharpe de référence
de 0,0332 par trade :

| portes ouvertes | seuil déflaté | part du Sharpe consommée |
|---|---|---|
| 0 | 0,0000 | 0 % |
| 1 | 0,0141 | 42 % |
| 5 | 0,0314 | 95 % |

Une configuration unique ne paie **aucune** taxe. C'est pourquoi la version
scellée ne garde que le déclencheur. La confluence n'est pas rejetée par goût :
elle est trop chère au regard de ce qu'elle doit financer.

Deux pièges déjà tombés dedans, à ne pas refaire :
- le contrôle d'échantillon doit partir de `REFERENCE_BITS` — l'effet à
  *détecter* — et jamais du taux de réussite *observé*, sinon un très mauvais
  résultat exige un petit échantillon et passe. Un test verrouille ce point.
- ne pas borner le budget par `max(2.0, ...)` : cela masque le fait ci-dessus
  et fait afficher +0 % à toutes les portes. **Le piège a été retrouvé dans
  ALP nº 3** : le bornage y fabriquait un seuil de 0,0215 à zéro levier, où la
  vraie valeur est zéro, et le papier annonçait « quatre leviers coûtent un
  facteur 2 » alors que c'était le rapport d'un levier à quatre. À zéro levier
  il n'y a qu'une configuration, donc rien à sélectionner et rien à déflater ;
  le premier levier fait un saut depuis zéro qu'aucun facteur ne mesure.

## Les figures se regardent, elles ne se relisent pas

Le code d'une figure peut être juste et la figure fausse. Trois défauts n'ont
été trouvés qu'en rendant la page dans un navigateur et en la regardant :

- **Un cadre entièrement vide.** Le troisième cadre de `couche_profil` avait
  un domaine fixé à 48-86 % alors que les probabilités calculées valaient 90 à
  93 %. `Panel.path` découpe au domaine : la courbe disparaissait sans erreur,
  et les points, qui ne se découpent pas, se posaient hors du cadre. Le cadre
  s'affichait vide dans les deux documents depuis sa création. **Un domaine se
  déduit des données, jamais l'inverse.**
- **Un tracé coupé en deux.** Même cause, effet plus discret : la trajectoire
  de `couche_carnet` sortait par le bas et le tracé perdait un morceau au
  milieu, ce qui se lit comme une interruption de la donnée.
- **Une phrase coupée en deux.** `extraire_pieds` sortait du SVG les lignes de
  pied une à une, sur un critère de longueur. Une phrase dont la dernière
  ligne tombait sous cinquante-cinq caractères se retrouvait moitié sous la
  figure, moitié dedans. La marque `cap`, posée par `Board.caption`, a
  remplacé le critère ; `Board.annotation` sert aux phrases qui doivent rester
  dans la figure.

Le même défaut a été retrouvé six fois, dont quatre dans ALP nº 1 : un
domaine écrit à la main, plus étroit que ce que la figure calcule. La surface
d'espérance de la figure 1 montrait des échardes verticales ; le sommet de
Kelly, seul objet du cadre qui le porte, était au-dessus du cadre ; les deux
mesures gaussiennes de la queue débordaient jusqu'à la ligne de lecture. La
cause commune était que `figures.Canvas` ne découpait pas au domaine, à la
différence de `figterm.Panel`. Il le fait maintenant — mais **le découpage est
un filet, pas une dispense : un domaine se déduit des données.**

Corollaire qui a mordu deux fois : **une légende écrite devant un cadre borné
décrit le bornage, pas la donnée.** « La surface est presque plate le long de
l'axe de l'edge » et « la surface change de signe dans les deux directions »
étaient toutes deux fausses, et toutes deux vraies de ce que la fenêtre
laissait voir. Élargir une fenêtre oblige à relire sa légende.

Deux balayages automatiques valent d'être rejoués après toute retouche de
figure ; ils tiennent en une trentaine de lignes chacun :

1. dans le navigateur, comparer la boîte rendue de chaque `text`/`rect`/`path`
   à celle du `<svg>` — cela attrape les débordements de viewBox — puis
   croiser les boîtes des `text` entre elles, ce qui attrape les étiquettes
   qui se recouvrent ;
2. en Python, envelopper `Panel.path` et `Panel.dot` pour signaler un tracé
   que le découpage réduit à moins de deux points, et une marque posée hors
   du cadre.

## Commandes

```
python main.py --tests      # 794 tests (compter ~20 min, --wp et figures sont lents)
python main.py --wp         # reconstruit le document de travail
python main.py --strategy   # rejoue la stratégie scellée et sa batterie
python main.py --bounds     # la mesure encadrée par les deux remplissages
python main.py --disc       # journal de décision, lois nulles, attribution
python main.py --discpaper  # reconstruit docs/prouver-un-jugement.html
```

## Contraintes d'environnement

Le réseau sortant ne joint que les registres de paquets et GitHub : **aucun
hébergeur de données de marché n'est atteignable**. Toute mesure se fait donc
sur série synthétique de vérité connue, ou sur un fichier fourni par
l'utilisateur au format décrit dans `docs/donnees-requises.md`.

Développement sur la branche `claude/project-main-file-l8ix6k`. Ne jamais
pousser ailleurs sans autorisation explicite. Pas de pull request sauf demande
explicite.

## Arbitrages ouverts — non tranchés, ils engagent le nom de l'auteur

1. Adopter le test directionnel : 39 % de trades en moins, mais impose un
   re-scellement du protocole préenregistré.
2. Remplacer le ratio de variance par la DFA dans le Test 1, le ratio de
   variance étant biaisé à Ĥ = 0,52 sur une vraie martingale.
3. Recalculer le chapitre des instruments à c = 0,65 au lieu de 0,33 —
   cela publierait des chiffres nettement moins favorables.
4. Points d'audit 4, 5 et 6 : câbler la batterie anti-surajustement et le
   journal d'exécution dans `measure.py`.
