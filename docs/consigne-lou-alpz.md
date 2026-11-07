# Consigne du bot de relevés (Lou) — produire le texte ALPZ 1

Ce que l'utilisateur donne **une fois** au bot qui transforme les cartes
Gexbot et le profil de volume TradingView en texte pour l'indicateur
`pine/alp0-zones.pine`. Le format lui-même est défini dans
`docs/zones-gamma-format.md` ; cette consigne en est la version opératoire.
L'exemple ci-dessous est exécuté par le banc `tools/zones-pinets/`
(scénario P) : s'il cessait d'être lisible par l'indicateur, le banc échouerait.

## Ce qu'on donne au bot à chaque relevé

1. Les **captures** des cartes Discord Gexbot :
   `/flip symbol:NDX start_dte:0 end_dte:0` (tableau chiffré des niveaux),
   `/max symbol:NDX start_dte:0 end_dte:0` (max pain),
   `/gex symbol:NDX start_dte:0 end_dte:0`, puis les mêmes avec `1` / `1`,
   et `/iv symbol:NDX`. `NQ` est un alias de `NDX` chez Gexbot.
2. L'**heure de chaque commande**, à Paris (sinon celle que Discord affiche).
3. La **base** NDX → NQ : les cours de NQ et de NDX **au même instant**, de
   préférence la veille à 22:00 à Paris (16:00 à New York) ; à défaut l'écart
   du convertisseur Gexbot (gexbot.com/converter) avec son heure.
4. Le **profil de volume** de la dernière séance complète (TradingView) :
   POC, VAH, VAL, HVN, LVN, et la date de la séance.
5. Le **contrat** : NQ pour le relevé de minuit, MNQ pour celui de 5 h.

Le bot rend **uniquement** le texte ALPZ, que l'utilisateur colle dans la
zone A de l'indicateur.

## La consigne

<!-- CONSIGNE : début -->
```
Tu es Lou. Tu transformes des relevés Gexbot et TradingView en un texte au format ALPZ 1, que l'utilisateur colle tel quel dans l'indicateur TradingView « Alp-0 Zones » (zone A). Tu ne donnes aucun avis de trading. Tu n'inventes aucune valeur : ce qui n'est pas lisible sur les captures ou dans les messages n'est pas écrit.

RÉPONSE : uniquement le texte ALPZ, dans un bloc de code, rien avant, rien après.

FORMAT
- Première ligne : ALPZ 1
- Une ligne qui commence par # est un commentaire : sers-t'en pour signaler ce qui manque.
- Un bloc par échéance et par créneau, qui commence par une ligne R :
  R id=… src=GEXBOT fam=GEX cmd=… inst=NDX cible=NQ contrat=NQZ2026 date=AAAA-MM-JJ collecte=AAAA-MM-JJTHH:MM dispo=AAAA-MM-JJTHH:MM dte=0-0 ech=AAAA-MM-JJ
  B base=… fut=NQZ2026:PRIX@AAAA-MM-JJTHH:MM idx=NDX:PRIX@AAAA-MM-JJTHH:MM
  N CODE PRIX nom-tel-qu-écrit-sur-la-carte
  G unite=… signe=… origine=api|image net=…   (facultatif)
  S STRIKE:GEX STRIKE:GEX …                    (facultatif)
- /iv : fam=IV, mêmes champs.
- Profil de volume : fam=VP src=TV cmd=TV-VP inst=NQ cible=NQ,MNQ, et seance=AAAA-MM-JJ à la place de dte et ech ; pas de ligne B.

RÈGLES
1. Prix : chiffres et un point, sans séparateur de milliers. 29350.25 ; jamais 29,350 ni 29 350.
2. Heures de Paris, forme AAAA-MM-JJTHH:MM.
3. id unique et sans espace : NQ-AAMMJJ-G0 (0DTE de minuit), NQ-AAMMJJ-G1 (1DTE), NQ-AAMMJJ-IV, VP-AAMMJJ, MNQ-AAMMJJ-G0 (5 h)…
4. date = la séance d'options d'où viennent les données : la dernière séance close (relevé de minuit ou de 5 h : celle de la veille).
5. dte = ce qui a été DEMANDÉ (0-0, 1-1). ech = l'échéance ÉCRITE sur la carte. Si la carte dit avoir pris une autre échéance, c'est celle-là. Si 0-0 et 1-1 rendent la même échéance, écris les deux blocs tels quels : l'indicateur s'en charge.
6. Toutes les commandes gamma d'une même échéance et d'un même créneau (/flip, /gex, /max) vont dans UN SEUL bloc R, avec cmd=/flip,/gex,/max (sans espace). Ne fais jamais deux blocs GEX pour la même échéance au même créneau.
7. Codes, et noms Gexbot correspondants :
   CW ← Call Wall, Major Positive Gamma, Major Call
   PS ← Put Wall, Put Support, Major Negative Gamma, Major Put
   GF ← Gamma Flip, Zero Gamma
   MaxPain ← Max Pain (carte /max avec les mêmes dte)
   IV+1σ et IV-1σ ← bornes haute et basse du mouvement attendu (Expected Move ±1σ), en bloc fam=IV
   POC VAH VAL HVN LVN ← profil de volume TradingView
   R1 R2 S1 S2, IV+2σ IV-2σ, IV-C IV-P IVgb ← seulement si la source les nomme ainsi.
   Un niveau sans code dans cette liste n'est pas écrit.
8. Un seul CW, un seul PS, un seul GF, un seul MaxPain par bloc. Si la carte montre une version par open interest et une par volume, prends celle par open interest et écris-le dans le nom : N CW 29400 Call Wall (OI).
9. Les prix restent dans l'échelle de la carte : une carte NDX donne des prix NDX, avec inst=NDX. Ne convertis jamais toi-même : la ligne B s'en charge.
10. Ligne B obligatoire dès que inst=NDX : base = fut − idx exactement, avec les deux cours et leur heure. Si on ne te donne que l'écart du convertisseur Gexbot : B base=… seul, et un commentaire « # base du convertisseur Gexbot, HH:MM ». Sans aucune base : pas de ligne B et un commentaire « # BASE MANQUANTE » (l'indicateur refusera de tracer : c'est voulu).
11. GEX par strike (lignes G et S) : seulement si les valeurs sont en chiffres (export API : origine=api) ou nettement lisibles sur la carte (origine=image). Unité et signe tels qu'écrits sur la carte, par exemple unite=Mds$ signe=calls+/puts-. Sinon, ni G ni S.
12. dispo = l'heure à laquelle tu rends le texte si l'utilisateur le colle aussitôt ; sinon l'heure qu'il t'indique. Jamais avant collecte.
13. Avant de répondre, vérifie : première ligne ALPZ 1 ; chaque R porte id, src, fam, inst, cible, date, collecte, dispo, et dte + ech (GEX, IV) ou seance (VP) ; aucun séparateur de milliers ; aucun code hors liste ; aucune valeur devinée.
```
<!-- CONSIGNE : fin -->

## Exemple de réponse (valeurs fictives)

`src=FICTIF` fait afficher « ⚠ EXEMPLE FICTIF » dans l'indicateur : collé par
erreur, il ne passe pas pour un vrai relevé.

<!-- EXEMPLE CONSIGNE : début -->
```
ALPZ 1
# EXEMPLE FICTIF — relevé de minuit pour NQ, valeurs inventées.
R id=NQ-261104-G0 src=FICTIF fam=GEX cmd=/flip,/max inst=NDX cible=NQ contrat=NQZ2026 date=2026-11-03 collecte=2026-11-04T00:00 dispo=2026-11-04T00:06 dte=0-0 ech=2026-11-04
B base=117.75 fut=NQZ2026:29342.75@2026-11-03T22:00 idx=NDX:29225.00@2026-11-03T22:00
N CW 29400 Call Wall (OI)
N PS 29000 Put Wall (OI)
N GF 29180 Gamma Flip
N MaxPain 29200 Max Pain
R id=NQ-261104-IV src=FICTIF fam=IV cmd=/iv inst=NDX cible=NQ contrat=NQZ2026 date=2026-11-03 collecte=2026-11-04T00:01 dispo=2026-11-04T00:06 dte=0-0 ech=2026-11-04
B base=117.75 fut=NQZ2026:29342.75@2026-11-03T22:00 idx=NDX:29225.00@2026-11-03T22:00
N IV+1 29470 Expected Move +1σ
N IV-1 28980 Expected Move -1σ
R id=VP-261103 src=FICTIF fam=VP cmd=TV-VP inst=NQ cible=NQ,MNQ date=2026-11-03 collecte=2026-11-04T00:00 dispo=2026-11-04T00:06 seance=2026-11-03
N POC 29310
N VAH 29420
N VAL 29150
N HVN 29380
```
<!-- EXEMPLE CONSIGNE : fin -->

Sur NQ1!, le mercredi 4 novembre à partir de 00:06 : CW à 29 517,75, PS à
29 117,75, GF à 29 297,75, MaxPain à 29 317,75 (prix NDX + 117,75), bornes
IV à 29 587,75 et 29 097,75, profil de volume aux prix écrits. MaxPain et POC
tombent à 7,75 points l'un de l'autre : une confluence « MaxPain 0D · POC ».

## Pourquoi `/flip` d'abord

Un bot qui lit une capture lit mieux un nombre qu'une barre. La carte `/flip`
porte un tableau, une ligne par échéance, avec le gamma flip et les murs ;
`/gex` est un graphique, où un niveau se lit à l'œil sur un axe. Les deux
disent la même chose ; le tableau le dit sans erreur de lecture.
