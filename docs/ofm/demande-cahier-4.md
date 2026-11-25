# Demande du cahier nº 4 (25 nov. 2026)

## Ses mots
> Étudie le marché du sex et tout ce qui est lié au business ofm, je veux que tu te bases sur des études prouvées et
> non arbitré par le marché de l'ofm pour chiffrer plus que 99% de ma concurrence en ayant un edge sur ce marché et
> capturer la plus grosses parts en premier, prend en compte sur plein de gens on sûrement pensé comme moi donc on
> adapté, et que d'autres une plus petites masses à aussi prévu ça ect ect donc prend ça en compte pour capturer l'edge
>
> Crée un plan une formation avec tout de détails normalement et simplement en expliquant bien pourquoi et si tu peux
> backtester avec les meilleurs outils quant au monde dispo sur le marché ou dev t'es propre outils non arbitrer par le
> marcher sa sera une grosse avancée
>
> Donne le en fichier ici et on verra pour le mettre sur l'app
>
> En gros t'arrête pas tant que t'as pas trouvé d'edge qui a été vérifié par tout les stress test possible

## Ce que ça veut dire
- **Le marché** : taille, croissance, concentration (qui prend l'argent), ce que veulent les fans, ce qui menace le
  marché (paiement, réglementation, procès). Chiffres sourcés et vérifiés, jamais « souvent repris ».
- **La concurrence en niveaux** : niveau 0 = suit les guides ; niveau 1 = a vu le niveau 0 et s'adapte ; niveau 2 = a
  prévu le niveau 1… Mesurer combien de coups d'avance les gens pensent vraiment (Nagel 1995, Camerer-Ho-Chong 2004),
  combien un avantage s'use quand il se sait (McLean-Pontiff 2016), si être premier suffit (Golder-Tellis 1993).
- **Une avance** = ce qui rapporte plus que la règle de la foule, **hors échantillon**, et qui **ne s'use pas** (ou
  peu) quand les autres la copient.
- **Tous les stress tests** : une batterie déclarée d'avance, appliquée à chaque avance ; un test qui ne s'applique pas
  est dit « sans objet », jamais compté comme réussi.
- **Les outils** : ceux des meilleurs quants (Reality Check, SPA, Romano-Wolf, PBO/CSCV, Sharpe dégonflé, seuil t ≥ 3,
  courbe de spécification), réécrits en bibliothèque standard et **recoupés** avec les bibliothèques de référence ;
  plus un outil à nous : **l'arène** (concurrence en niveaux, simulée sur tout un domaine de paramètres).
- **Le livrable** : un fichier (page mobile dans la DA de Lueur) envoyé dans la conversation, plus un JSON de valeurs
  pour l'app plus tard. Plan de A à Z + formation (en clair, à 5 ans, exemple, pourquoi, comment le vérifier chez soi).

## Garde-fous (règle de la maison, skill `ofm`)
Aucune tactique qui fasse passer un chatteur pour la créatrice ; rien qui vise un fan en détresse ; aucun dark pattern
(faux compte à rebours, case cochée pour payer) ; consentement et limites des créatrices écrits ; aucune mineure.
Une avance qui ne tient que par la tromperie n'est pas une avance : elle est rangée dans « ce qui ne marche pas ».

## Honnêteté
Aucune donnée d'OnlyFans n'est publique : on teste sur des marchés voisins (tirés au sort quand c'est possible) et on
le dit. « Vérifié par tous les stress tests » veut dire : par la batterie déclarée, sur ces données. La formation
finit toujours par « comment le vérifier chez soi » (groupe témoin).

## AVANCEMENT
- [x] Demande écrite (ce fichier).
- [x] Études et chiffres du marché vérifiés (recherches du 25 nov. ; module `ofm/litterature4.py` à écrire).
- [x] Registre nº 4 écrit et commité **avant** tout calcul (`ofm/registre4.py`, 25 tests + 4 affirmations de l'arène).
- [ ] Batterie de stress (`ofm/stress.py`) étalonnée sur vérité connue.
- [ ] Outils recoupés avec les références (`ofm/donnees/RECOUPEMENT4.json`).
- [ ] Avances testées sur données réelles (`ofm/avances.py`, nouveau jeu : Open Bandit Dataset, échantillon GitHub).
- [ ] Arène (`ofm/arene.py`).
- [ ] Synthèse et verdicts (`ofm/synthese4.py`).
- [ ] Plan et formation (`ofm/formation4.py`, `ofm/clair4.py`).
- [ ] Page, graphiques, tests (`ofm/figmobile4.py`, `ofm/mobile4.py`, `ofm/tests/test_ofm4.py`).
- [ ] Fichier livré, mémoire à jour, poussé.
