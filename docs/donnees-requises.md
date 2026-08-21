# Ce qu'il manque, et comment le fournir

Le dépôt obtient **90,2 points sur 100** à la grille de notation qu'il
s'applique à lui-même (`alp1/grading.py`, `python main.py --alp2`). Les dix
points manquants sont tous au même endroit, et un seul objet les débloque :
**un historique de prix.**

| Critère | Poids | Note | Ce qui bloque |
|---|---|---|---|
| b1 — Données de marché mobilisées | 10 | 1 / 5 | Aucune série de prix n'a été ouverte. |
| b3 — Candidat de dérive | 9 | 4 / 5 | La dérive est reprise de tiers, jamais ré-estimée. |
| **Tous les autres** | 81 | **5 / 5** | — |

Aucun raisonnement, aucune démonstration, aucun raffinement de modèle ne peut
lever ces deux réserves : ce sont des critères qui portent sur une **mesure**,
et une mesure exige des données. La chaîne qui les consomme est écrite,
auditée et testée ; il lui manque un fichier.

---

## 1. Avant de m'envoyer quoi que ce soit : publier le sceau

**Cette étape vient en premier, et elle est gratuite.**

```bash
python main.py --prereg
```

La commande imprime l'empreinte SHA-256 du protocole gelé — configurations,
règle de décision, seuils, règles d'arrêt, critères de falsification, et les
nombres de calibration eux-mêmes. Publiez cette empreinte quelque part
d'horodaté et d'immuable **avant** que le premier fichier de prix n'entre dans
le dépôt : un commit signé, un message daté, peu importe le support.

Ce que cela vous achète : le jour où la mesure donne un résultat favorable,
vous pourrez montrer que la règle n'a pas été choisie après l'avoir vu. Sans
cette étape, un bon résultat n'est pas distinguable d'un résultat choisi, et le
seuil déflaté du document ne veut plus rien dire. C'est le seul point de tout
le protocole qui coûte zéro et rapporte tout — et le seul qu'il soit
définitivement trop tard pour faire après.

---

## 2. Fichier A — les prix (indispensable)

### Format

Un CSV de barres d'une minute. Un exemple exact est fourni :
[`docs/exemple-format.csv`](exemple-format.csv).

```csv
timestamp,open,high,low,close,volume
2026-01-02 09:30:00,5901.25,5903.50,5900.75,5902.00,1843
2026-01-02 09:31:00,5902.00,5904.25,5901.50,5903.75,1204
```

Les noms de colonnes sont reconnus sans distinction de casse et dans n'importe
quel ordre ; `datetime`, `date_time` ou `time` sont acceptés à la place de
`timestamp`, et une paire `date` + `time` séparée fonctionne aussi. La colonne
`volume` est facultative — son absence ne désactive que les tests de profil de
volume, aucun des tests du protocole.

### Les quatre exigences qui comptent

1. **Horodatage en heure de l'échange (ET), pas en UTC.** Une séance décalée
   d'une heure déplace la bande de bruit et fausse toutes les cassures. Le
   lecteur vérifie que les séances ouvrent bien à 09:30 et refuse le fichier
   sinon.
2. **ISO 8601.** `2026-01-02 09:31:00` ou `2026-01-02T09:31:00Z`. Les formats à
   barres obliques commençant par le jour ou le mois — `01/02/2026` — sont
   **refusés et non devinés** : ils sont ambigus, et une inversion silencieuse
   décale tout l'historique sans lever la moindre erreur.
3. **Contrat continu ajusté aux roulements**, ou un seul contrat à la fois. Un
   saut de roulement non ajusté vaut plusieurs points — exactement l'échelle du
   signal recherché.
4. **Séance régulière** (09:30–16:00 ET). Les barres hors séance sont écartées
   automatiquement ; les fournir ne gêne pas.

### Combien, et sur quoi

| Grandeur | Valeur | Pourquoi |
|---|---|---|
| Instrument | ES, MES, ou SPY à défaut | La littérature retenue porte sur SPY et sur ES/NQ ; les trois sont recevables. |
| Profondeur | **5 ans minimum**, 10 confortable | Le protocole exige 1 000 trades avant de conclure, soit environ cinq ans à un trade par séance. |
| Granularité | 1 minute | La bande de bruit se mesure à la minute ; la barre de 5 minutes fait perdre l'instant de cassure. |
| Volume | apprécié, non requis | — |

Avec moins de 1 000 trades, la chaîne tourne et rapporte tout, mais le
protocole **refuse de conclure** — c'est écrit dans la règle de décision, et
c'est délibéré.

### Où le trouver

Je n'ai pas d'accès réseau depuis cette session : je ne peux ni télécharger ces
données ni vérifier les conditions actuelles des fournisseurs. La liste
ci-dessous est indicative et à recouper.

**Payant, quelques dizaines d'euros pour l'historique complet** — c'est la voie
courte :

- **FirstRate Data** — ES continu à la minute, historique long, achat unique.
- **Databento** — CME en direct, granularité jusqu'au carnet, facturation à la
  consommation. Le plus propre si le budget suit.
- **Kibot**, **Norgate Data** — futures continus ajustés, formules annuelles.

**Par votre courtier, souvent inclus :**

- **Interactive Brokers** (API TWS) — historique à la minute, mais la
  profondeur disponible sur les futures est courte ; à vérifier pour votre
  compte.
- **Rithmic**, **CQG**, **Tradovate** — selon l'abonnement de données déjà payé
  pour trader.

**Gratuit, en repli :**

- **SPY à la minute** via un fournisseur d'actions à historique long. C'est le
  support de l'article fondateur : ce n'est pas un pis-aller, c'est la série
  d'origine. Attention à la conversion — SPY vaut environ un dixième de
  l'indice, et la friction doit être recalculée pour l'action, pas pour le
  futur.
- Les API gratuites d'usage général ne donnent en général qu'un mois de
  granularité minute : insuffisant, et je préfère le dire que vous le laisser
  découvrir.

---

## 3. Fichier B — le gamma net quotidien (facultatif)

Nécessaire uniquement pour la configuration **C2**, celle qui conditionne au
signe du gamma des teneurs. Les configurations C1 et C3 tournent sans.

```csv
date,gamma_net
2026-01-02,-1.42e9
2026-01-05,3.10e9
```

Seul le **signe** entre dans le protocole. Une seule valeur par séance, connue
à l'ouverture — jamais une valeur de clôture, qui contiendrait l'information de
la séance qu'on cherche à prédire.

Sources : les fournisseurs spécialisés publient un niveau quotidien ; à défaut,
`alp1/gex.py` sait le reconstruire à partir d'une chaîne d'options de fin de
séance, ce qui exige de collecter cette chaîne jour après jour — c'est le seul
élément du dispositif qu'on ne peut pas rattraper rétrospectivement.

---

## 4. Où déposer les fichiers, et quoi lancer

Placez les fichiers dans un répertoire `data/` à la racine (il est ignoré par
git — vos données ne partiront pas dans le dépôt), puis :

```bash
python main.py --measure data/es-1min.csv                 # C1 seule
python main.py --measure data/es-1min.csv data/gamma.csv  # C1, C2 et C3
```

La commande commence par **auditer** le fichier et refuse de mesurer s'il n'est
pas propre : couverture des minutes attendues sous 95 %, séances n'ouvrant pas
à l'heure (le symptôme d'un horodatage en UTC), barres incohérentes. Elle vous
dit lequel des trois, et rien d'autre ne se produit.

Le fichier propre, elle imprime l'enchaînement des tests, chacun avec son
critère d'arrêt, puis la décision rendue par la règle scellée.

Pour voir à quoi ressemble la sortie sans avoir de données, la chaîne tourne
sur une série synthétique dont la vérité est connue :

```bash
python main.py --measure
```

---

## 5. Ce que la mesure change, et ce qu'elle ne changera pas

| Résultat de la mesure | b1 | b3 | Total |
|---|---|---|---|
| Aucune donnée (aujourd'hui) | 1 | 4 | 90,2 |
| Historique mesuré, dérive confirmée au-dessus du seuil | 5 | 5 | 100 |
| Historique mesuré, dérive infirmée | 5 | 5 | 100 |

Les deux dernières lignes sont identiques, et ce n'est pas une erreur : la
grille note la **conduite d'une mesure**, pas son résultat. Un protocole qui
mesure et conclut que l'effet n'est pas là vaut exactement autant qu'un
protocole qui le trouve — c'est même le seul cas où la note est méritée sans
ambiguïté, puisque personne n'a intérêt à ce résultat-là.

Ce que la mesure ne changera pas : elle ne rend pas la stratégie rentable et ne
prouve pas qu'elle l'est. Elle remplace une hypothèse reprise de tiers par une
estimation faite sur vos données, avec un seuil fixé d'avance. C'est tout, et
c'est la seule chose qui manque.

---

## 6. Plus tard — le journal d'exécution

Le cinquième test du protocole ne se conduit pas sur historique : il compare le
prix que vous obtenez à celui que le modèle suppose. Une ligne par trade —
heure de cassure, prix théorique, prix obtenu, sortie, motif — suffit.

Ce test décide d'un chiffre dont tout le reste dépend : la friction. Le module
`alp1/friction.py` la **déduit** aujourd'hui du barème, de la profondeur du
carnet, de la latence et de la volatilité de déclenchement, et trouve 0,65
point en moyenne — le double de ce que le document posait au départ. Si votre
journal montre davantage, toutes les marges du document sont à refaire avec
votre chiffre, et le module sait le faire : c'est un paramètre du `Venue`, pas
une constante.
