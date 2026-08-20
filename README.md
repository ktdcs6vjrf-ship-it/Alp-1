# Alp-1

Formalisation, diagnostic quantitatif et protocole de validation d'une stratégie
discrétionnaire intraday sur futures indiciels à sept couches.

Le paper complet : [`docs/alp1-paper.html`](docs/alp1-paper.html).

## Le résultat central

Sous un mouvement brownien sans drift, l'espérance par trade vaut exactement
`−c/L` — la friction rapportée au risque nominal — **quel que soit le ratio
gain/risque retenu**. Le placement des barrières ne crée aucune espérance ;
seul un drift à l'entrée le peut, et la friction est un prélèvement forfaitaire
invariant au réglage du R:R.

Conséquence appliquée au stop d'origine (0,005 %–0,010 % de l'indice, soit 1 à
2 ticks sur ES) :

| Stop | Ticks | Friction / risque | P(stop par le bruit, 1 min) |
|---|---|---|---|
| 0,005 % | 1,2 | 1,10 | 81,0 % |
| 0,010 % | 2,4 | 0,55 | 63,1 % |
| 0,050 % | 12,0 | 0,11 | 1,6 % |

## L'edge proposé — Gamma-Regime Conditioning

La pile fait tourner en permanence deux moteurs contradictoires : Dow
(continuation) et VWAP ± k·SD (réversion). Le signe du gamma dealer net les
arbitre sur une base mécanique :

- **Γ > 0** — couverture contra-tendancielle, volatilité comprimée → régime de
  réversion : les bandes VWAP tiennent, les cassures sont fausses.
- **Γ < 0** — couverture pro-cyclique, volatilité amplifiée → régime de
  momentum : fader une bande revient à se placer contre un flux de hedging forcé.
- **Γ ≈ 0** — voisinage du flip level, régime instable → aucune entrée.

Le GRC rétrodit une anomalie observée empiriquement avant toute considération de
gamma (« SD3 à éviter, gros swipe and close »), ce qui en constitue un premier
test hors échantillon.

## Utilisation

```bash
python main.py            # génère les tables quantitatives du paper
python main.py --tests    # 29 tests unitaires du noyau
```

Aucune dépendance : stdlib uniquement, Python 3.11+.

## Structure

| Module | Rôle |
|---|---|
| `alp1/costs.py` | Modèle de friction, hit rate d'équilibre, taille d'échantillon, déflation du Sharpe |
| `alp1/barriers.py` | First-passage brownien : survie du stop, P(TP avant SL), drift requis |
| `alp1/regime.py` | Classification GRC et playbooks par régime |
| `alp1/signals.py` | Les 7 couches formalisées en prédicats testables |
| `alp1/report.py` | Génération des tables du paper |

## Statut

Analyse théorique et protocole. **Aucune validation empirique** — le GRC comme
les autres hypothèses restent à tester sur données historiques, dans l'ordre
indiqué au §8.3 du paper. Ce dépôt ne constitue pas un conseil en investissement.
