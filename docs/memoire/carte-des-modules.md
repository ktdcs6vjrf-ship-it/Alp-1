# Carte des modules, pine et hors-noyau

> Extrait de `CLAUDE.md` (déplacé tel quel, rien n'est réécrit). À lire quand on touche à ce sujet.

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
- `volga.py` — **la courbure en volatilité, et le sourire qu'on en tire.**
  `volga` et ses deux contrôles `volga_par_vega` / `volga_par_prix` ;
  `bande_negative`, qui **importe** celle du vanna plutôt que de la récrire, et
  `decalage_de_portage`, qui chiffre ce qui la sépare de celle de la partie
  XXII ; `ecart_a_la_corde` (la droite et la crosse) ; `crete_du_volga`, balayé
  et non résolu ; les trois routes du sourire — `sourire_naif`,
  `sourire_second_ordre`, `sourire_exact` par `prix_exact` en quadrature —
  et `retournement`, qui exige un véga non négligeable ;
  `poids_de_la_correction` et `pic_du_poids`, dont la mesure **retourne** le
  critère usuel de validité ; `PLANCHER_INVERSION` et `tenor_inversible`, le
  ténor sous lequel une inversion ne rend plus qu'un bruit d'arrondi ;
  `perte_du_vendeur` / `rapport_des_chocs` / `part_du_second_ordre` ; et
  `Papillon`, dont `poids_neutre` **résout** le véga net au lieu de l'écrire.
  Huit tables, quatre surfaces.
- `figvo.py` — les quinze planches de la partie XXVI, dont quatre reliefs.
- `ordres.py` — **les cinq grecs du troisième ordre, et leur contrôle.**
  `speed`, `zomma`, `color`, `veta`, `ultima`, chacun avec sa route
  indépendante (`speed_numerique`, `zomma_numerique`, `ultima_numerique`) —
  la règle du dépôt appliquée à cinq objets neufs. `DEMI_HAUTEUR` =
  `√(2 ln 2)`, **importé de l'idée de la partie XIX**, avec
  `mouvement_de_demi_gamma` / `_mesure` et `echeance_du_pour_cent` (0,429 j).
  Les deux lois d'horloge sans paramètre : `gamma_demain_simple` = `√(T/(T−Δt))`
  et `vega_perdu_simple`, leurs mesures, et `ecart_de_portage` — la loi en
  racine n'est exacte **qu'à portage nul**, et c'est le portage qui domine les
  deux écarts. `racines_ultima` = `(3 ± √(9+4σ²T))/2`, `minimum_de_d1d2` =
  `−σ²T/4` et `moneyness_du_minimum` = `e^{−(r−q)T}` — le minimum est au
  **forward**, ce qui rend la racine négative inatteignable et règle le nombre
  de bascules sans balayage. `bande_zomma` / `bande_ultima` /
  `rapport_au_volga`, les trois seuils du même produit ; `_traversees`, qui
  balaie **puis affine par bissection**. `campagne` sur `COUPLES` et
  `pire_part` : la part de variance que quatre grecs expliquent, livre nu et
  livre couvert, sur tirage joint à corrélation déclarée. Six tables, quatre
  surfaces.
- `figord.py` — les quatorze planches de la partie XXVII, dont quatre
  reliefs. Trois pièges de rendu y sont refermés : la planche de variance
  publie des **haltères** et non des barres (l'axe est tronqué, une barre y
  mentirait), celle de l'horloge porte un **axe logarithmique** (deux lois de
  puissance s'effondrent contre le bord gauche d'un axe linéaire), et la
  planche d'Ultima ne pose plus de point à la monnaie sur la ligne de zéro
  (il y valait 235 fois moins que le pic et se lisait comme une troisième
  bascule).
- `implicite.py` — **le nombre qu'il faut mettre dans le modèle.**
  `bornes_d_arbitrage` et `existe`, qui font de l'inversion une fonction
  **partielle** ; `implicite` par bissection et `implicite_newton` par le
  véga, les deux routes dont l'accord est le contrôle — et dont le désaccord,
  dans l'aile courte, *est* le plancher numérique de la partie XXVI.
  `points_de_vol_par_tick` = `100·tick/𝒱` et son contrôle par réinversion ;
  `strike_du_point_de_vol` et **`moneyness_cotable`**, les deux frontières
  que le guide ne nomme pas, cherchées du côté hors de la monnaie ;
  `ecart_a_la_droite`, qui mesure ce que la réciproque s'écarte de sa corde
  (0,9 % à la monnaie, 43 % dans l'aile). `serie` — un Ornstein-Uhlenbeck en
  logarithme, **amorcé dans son régime stationnaire**, graine explicite ;
  `iv_rank` / `iv_percentile` et leurs sensibilités, `borne_du_rapport`
  moyennée sur deux cents tirages parce qu'un tirage unique n'est pas
  monotone. `echantillon_effectif` = `n(1−ρ)/(1+ρ)` et sa mesure par la
  dispersion d'un percentile ; `seances_pour_distinguer`.
  **`implicite_juste`**, l'espérance conditionnelle de la réalisée à venir en
  forme fermée — c'est elle qui fait du gain une loi nulle — et
  `biais_de_look_ahead`, dont le champ `esperance` contrôle que la loi nulle
  en est une. `campagne`, qui publie **les deux comptabilités** du même livre,
  `biais_d_unite` et sa forme fermée `σ/(4h)`. `derive_par_deplacement` =
  `−Δ·ΔS/𝒱` (le signe a coûté un défaut), son contrôle, et
  `ecart_du_premier_ordre`, qui chiffre ce que le premier ordre manque au
  lieu de le qualifier. `pieges()`, dont le cinquième est la **somme** des
  quatre autres, et un test l'exige. Dix tables, quatre surfaces.
- `figiv.py` — les seize planches de la partie XXVIII, dont quatre reliefs.
  Deux d'entre elles ont été refaites après avoir été **regardées** : la
  planche de l'inversion annonçait une pente qui diverge et montrait une
  droite, et la surface du pas de cotation portait une moneyness là où seul
  un delta décrit le même objet à deux échéances.
- `skew.py` — **la forme, et trois façons de la mesurer.** `peau`, une
  surface **déclarée et non ajustée** dont la pente *et la courbure* portent
  le même exposant d'aplatissement — le premier jet ne le faisait que pour
  la pente, et le résultat de la partie s'y dégradait de moitié.
  `moneyness_du_delta`, qui résout le point fixe delta-volatilité-strike ;
  `risk_reversal` et son contrôle `risk_reversal_ferme` (`2·d·σ√T·|b|·σ`) ;
  `pente_moneyness_fixe`, `pente_a_la_monnaie`, `largeur_sondee` et
  `LARGEUR_FIXE` — c'est de la différence de ces deux bandes que découle
  toute la partie. `exposant_mesure` et **`decalage_des_exposants`**, un
  demi, stable au centième sur la grille de `H` : le résultat.
  `seuil_de_correlation` = `z/√(n−1)`, contrôlé contre `loi_nulle_du_test`
  (quatre mille tirages de Spearman) ; `seances_pour_correlation` par la
  transformation **exacte** de Fisher, et `borne_de_l_approximation`, qui
  dit *laquelle des deux bornes lie* — l'information ou la validité de
  l'approximation. `REGIMES` et `delta_du_regime`, dont la correction porte
  le **véga** (partie XXIV, importée) ; `etendue_a_la_monnaie_ferme`, qui ne
  dépend pas de l'échéance ; `options_pour_une_friction`, le nombre que le
  guide ne donne pas et qui rend sa phrase lisible. `delta_net_ferme` = `2δ`
  et `risk_reversal_position`, dont le véga net est nul par parité et le
  seuil passe sous le plancher plausible. `forces()`, les trois mécanismes
  avec le budget d'information de chacun. Neuf tables, quatre surfaces.
- `figsk.py` — les seize planches de la partie XXIX, dont quatre reliefs.
  Deux d'entre elles ont été refaites après avoir été **regardées** : la
  planche de la position montrait deux horizontales contre l'échéance, là où
  l'axe du delta fait apparaître l'identité `net = 2δ` ; et le relief des
  régimes portait une légende qui annonçait un sommet aux échéances longues
  sur une arête plate.
- `speculation.py` — **ce qu'une lecture vaut si l'on prend position.**
  `Issue` et `lire` (les trois issues, session comprise, dans les deux sens) ;
  `portee_de_seance` et `rr_atteignable`, les deux nombres qui disent si un
  rapport déclaré existe ; `stop_de_portee_un`, la frontière en forme
  fermée ; `derive_de_wald` / `derive_non_bornee` / `ecart_des_routes`, les
  deux seuils et le facteur qui les sépare ; `ecart_directionnel` et
  `horizon_optimal`, **borné par la séance** parce que l'affirmation l'est,
  avec `portee_de_l_optimum` qui vaut un ; `HYPOTHESES` et `bandeau`, la
  source unique du bandeau de chaque figure, dont l'avantage déclaré vaut
  zéro partout **parce que les modules qui l'ont mesuré rendent zéro** ;
  `_PREFIXES`, relevée sur les clés réelles et gardée par un test ;
  `familles_par_geometrie`, qui **calcule** le regroupement au lieu de
  l'écrire. Neuf tables, quatre surfaces.
- `figspec.py` — les quinze planches de la partie XXX, dont quatre reliefs.
- `pieds.py` porte en plus `bandeau_html` : la ligne de spéculation sous
  chaque figure, passée par `figure_html` avec la clé de la figure. Seul
  `discpaper` la passe ; les deux autres documents sont rendus comme avant.
- `report*.py` — chacun fournit `values()` et `all_tables()`. `report9` :
  stratégie. `report10` : ALP nº 3. `report11` : le seuil. `report13` : le
  risque refait. `report14` : flux, TPO, information, spectre. `report15` :
  l'audit de l'hypothèse d'edge d'ALP nº 1 — **la colonne de verdict de la
  table `dependance` est calculée, jamais écrite** ; l'ordre des lignes en
  découle, et un test l'exige.
- `fig*.py` — vingt-sept modules, chacun expose `render_all()`. `figcat.py` porte
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
  Piège enterré, et c'est celui qui ne se signale pas : `base = NQ − NDX` n'est
  juste qu'**au même instant**. Un abonnement qui livre le future en différé de
  quinze minutes et l'indice autrement fait soustraire deux instants
  différents, et la base absorbe la dérive de l'indice sur l'intervalle — des
  dizaines de points, l'ordre de grandeur de la base elle-même. L'indicateur ne
  suppose donc aucun retard : il demande à l'indice l'**horodatage** de la
  barre d'où vient son cours, écarte toute barre désalignée, et publie au
  panneau le désalignement mesuré, le nombre de barres retenues, la base brute
  qu'on aurait eue sans le filtre, et le retard du graphique contre l'horloge
  murale. Sans barre alignée il refuse de publier un nombre et trace en
  pointillé. Ce que le retard ne casse pas : les niveaux (la base dérive de
  0,2 point par quart d'heure, calculé). Ce qu'il casse : la colonne
  « distance au prix », qui parle d'un prix vieux d'autant — désactivée par
  défaut pour cette raison.
  Rendu : un objet `line` ne dépose **rien** sur l'échelle des prix, c'est un
  dessin et pas une série. Le prix d'un niveau y arrive donc par **douze
  emplacements `plot` fixes**, tracés en `display.price_scale` seul — ils ne
  dessinent rien dans le panneau, où le trait pointillé fait tout le travail.
  Douze est une limite dure : le nombre de `plot` d'un script est fixé à la
  compilation et ne peut pas suivre une liste. Trois pièges de langage y sont
  refermés : `display` n'accepte qu'une **constante**, donc l'interrupteur vide
  la série au lieu de changer le paramètre ; les trois tableaux naissent à la
  taille douze remplis de vide, pour qu'`array.get` ne soit jamais hors bornes
  quelle que soit la façon dont Pine évalue la branche non prise d'un ternaire ;
  et l'intitulé en bout de trait est une bulle `style_label_left` rendue
  **totalement transparente**, seule façon de caler un texte à gauche de son
  ancre sans cartouche. Les trois familles se distinguent par la valeur **et**
  par le motif de trait, jamais par la teinte seule.
  **`R1 R2 S1 S2` sont la seule chose que ce fichier calcule** au lieu de la
  reporter : les plus fortes concentrations de gamma de part et d'autre du
  prix, tirées du bloc CSV du même collage, hors de celles qui portent déjà un
  nom. Le poids d'un strike est la **somme des valeurs absolues de ses
  jambes** — un call et un put au même strike y concentrent tous les deux du
  gamma et leurs signes opposés ne doivent pas s'annuler. Les colonnes se
  lisent dans l'en-tête du CSV, jamais à une position supposée. Le classement
  vient **après** la lecture entière (pour que les zones nommées soient déjà
  posées donc exclues) et **après** que la base soit tranchée (« au-dessus du
  prix » n'a de sens qu'à échelles ramenées à la même). Un export réel rend
  huit zones d'un seul collage.
  Vocabulaire : `codeDe` range les noms longs d'un robot sous les codes courts
  de l'opérateur — `PS` put support, `CR` call resistance, `MP` max pain,
  `GW` gamma wall, `HVL` gamma flip, `RM` résistance macro, `R1/R2/S1/S2`
  gardés tels quels. **L'ordre des tests porte le sens** : « major wall » se
  range en `GW` avant que « wall » ne le fasse basculer, « resistance macro »
  en `RM` avant que « resistance » ne le prenne. Le **préfixe d'échéance ne
  s'écrit pas à la main** : il se lit dans `## Context` (`horizon: 0 dte` →
  `0CR`), et c'est la seule raison pour laquelle cette section est lue. Coller
  deux exports d'échéances différentes à la suite donne donc `0CR` et `30CR`
  sur la même planche. `RM` est exempt de préfixe — « macro » *est* son
  échéance. Les zones partagent **un trait, une teinte, un style** (gris foncé,
  continu) : ce qui les distingue est leur nom, pas leur apparence. Vingt
  emplacements de `plot`.
  Lecture : l'export markdown entier d'un robot se colle **sans retouche**. Le
  sens de lecture est **déduit** (le nombre est à gauche ou à droite du
  séparateur selon le format) ; le nombre se nettoie de ce qui le décore mais
  **jamais du tiret**, sans quoi un niveau négatif deviendrait positif ; un
  titre `##` commute la lecture, ce qui fait tomber l'en-tête et le bloc CSV
  sans avoir à les reconnaître ; et une fenêtre de plausibilité autour du prix
  écarte les `22`, les `0` et les millésimes qu'un en-tête transporte — testée
  **avec et sans** la base, puisqu'on ne sait pas encore de quelle échelle le
  niveau parle. Deux niveaux au même prix ne font qu'un trait, et sa famille
  redevient neutre si les deux diffèrent : un mur d'appel et un mur de vente
  sur le même strike ne font pas un niveau d'appel.
  **L'échelle est mesurée, pas supposée** : un robot qui publie « NDX » peut
  publier des strikes d'indice ou des niveaux déjà portés sur le future, et
  rien dans le texte ne les distingue. L'indicateur compare la médiane des
  niveaux collés au prix avec et sans la base, publie les deux écarts, et en
  mode automatique retient le plus proche en écrivant lequel.
  La lecture se fait sur la **dernière** barre et non la première : c'est la
  seule où `close` est le prix courant, donc la seule où la fenêtre de
  plausibilité ait un sens. Les `plot` qui suivent lisent des tableaux déjà
  remplis, puisque Pine exécute le script de haut en bas à chaque barre.
  `tools/gex_lecture_sim.py` transcrit cette boucle en Python : **aucun
  compilateur Pine n'est joignable depuis le dépôt**, donc c'est la seule façon
  de vérifier qu'un collage rend les niveaux attendus sans ouvrir TradingView.
  Il ne participe ni aux documents ni aux tests.
  Piège de langage, trouvé par l'éditeur et pas par la relecture : **une ligne
  de continuation ne doit jamais être indentée d'un multiple de quatre.** Pine
  réserve ces indentations aux blocs locaux, donc une continuation posée à
  douze espaces se lit comme l'ouverture d'un bloc et rend
  « Syntax error at input end of line without line continuation ». Le fichier
  en portait deux sur quatre-vingt-six. Un balayage de quinze lignes les
  trouve — repérer les lignes qui finissent par un opérateur, lire
  l'indentation de la suivante — et il vaut mieux que l'œil, qui voit un
  alignement soigné là où le compilateur voit un bloc. Le `=> valeur` par
  défaut d'un `switch` est indenté de quatre **à juste titre** : c'est une
  branche, pas une continuation.
  Voir `docs/gex-discord-vers-tradingview.md`.
- `pine/alp0-zones.pine` — **étape 1** du cahier des charges « zones gamma,
  IV et VP » de l'utilisateur, plus le profil 0DTE de l'étape 2. Un seul
  indicateur : ⓪ la heatmap z-score des bougies — l'ancien « Z + Single
  Prints (OPEX) » de l'utilisateur, corrigé (nom trompeur, titre corrompu
  « ΓΣZera », zéro fabriqué en préchauffage remplacé par na, transparence
  perdue à l'éclaircissement, libellés 2σ/3σ figés, T2 ≤ T1) ; ① le VWAP et
  ses six bandes σ, VWAP précédent ±1/±2,
  étiquettes — réplique des réglages de « The Strategists - Aggregated VWAP »
  saisis sur le graphique (agrégation multi-places non reprise : sans objet au
  CME) ; ② le lecteur du format **ALPZ 1** que l'assistant Lou remplit à partir
  des commandes Discord Gexbot (spécification complète, exemple fictif et
  règles dans `docs/zones-gamma-format.md`) ; ③ niveaux gris pointillés de la
  disponibilité au **gel de 22 h** (posé à 22:00 exactes, appliqué à la
  bougie suivante) ; ④ CONFLUENCES (écart ≤ 8 pt ET diamètre ≤ 16 pt, prix
  jamais déplacés, minuit et 5 h jamais fusionnés) ; ⑤ touches et issues sur
  bougie confirmée — rejetée, cassée, ambiguë, non résolue ; ⑥ profil GEX signé
  0DTE à droite du prix, jamais reconstruit depuis CW/PS/GF.
  Premier retour de l'utilisateur (v2) : « je ne vois ni les lignes ni le
  profil ». Il avait installé le code de la première page (sans z-score) ;
  l'exemple est daté du vendredi, donc vu le week-end ses niveaux sont gelés
  à 22:00, une heure avant la dernière bougie ; et le profil, à 30 barres de
  la dernière bougie, était hors de l'écran d'un téléphone. Réponse v3 : la
  version en tête du tableau, une ligne **Lecture** (ce qui a été lu dans
  chaque zone), une ligne **Jour affiché** (en cours ou gelé, où regarder),
  la relecture par marqueurs d'un texte collé sans retours à la ligne, et le
  profil à 6 barres. **Leçon : un indicateur qui peut ne rien afficher pour
  de bonnes raisons doit dire lesquelles, à l'écran.**
  Deuxième retour (v3) : « aucune ligne ni graphique » encore, sans capture.
  Réponse v4 : un **mode démo** (groupe ⑤) qui ignore les zones de texte et
  pose des niveaux inventés en ‰ du prix d'ouverture (`rel=1` sur la ligne R,
  résolu à l'activation), datés de la séance de la dernière bougie
  (`last_bar_time`), marqués DÉMO partout. Il sépare les deux pannes
  possibles : si la démo s'affiche, c'est le texte collé ; sinon, c'est le
  script ou TradingView.
  Pièges enterrés : **une fonction Pine ne peut pas modifier une variable
  globale** (`n += 1` dans une fonction est refusé) — les compteurs vivent
  dans un tableau global (`cpt`), dont une fonction peut changer le contenu ;
  un ternaire qui contient `.get()` peut déborder si Pine évalue la branche
  non prise — on passe par un `if` ; sous quota, le premier jet dessinait les
  jours **les plus anciens** d'abord et sacrifiait le jour courant — trouvé par
  le scénario E du banc, corrigé (jour courant d'abord, zones vivantes avant
  les archives) ; la bougie de touche ne peut pas compter une réaction dont
  l'ordre par rapport à la touche est inconnu — seule la **clôture** au-delà
  du seuil la rend certaine.
  Gexbot (docs.gexbot.com, lu en novembre 2026) : fenêtres DTE inclusives et
  **cumulatives** ; fenêtre vide → première échéance suivante ; `NQ` est un
  alias de `NDX` ; cartes **image** en Discord, nombres par strike seulement
  par l'API Research ; rien n'est recalculé entre la clôture et l'avant-
  ouverture — donc à minuit comme à 5 h à Paris, `0-0` et `1-1` peuvent rendre
  **la même échéance** : le script le traite en doublon d'échéance.
- `tools/zones-pinets/` — **le premier banc qui exécute un fichier Pine du
  dépôt.** PineTS (runtime Pine v6 libre de LuxAlgo, `pinets@0.13.1`)
  transpile le vrai fichier et l'exécute sur des bougies synthétiques ; le
  banc lit lignes, étiquettes, boîtes, cellules de tableau et couleurs de
  `plotcandle`. 131 contrôles, dont l'exemple fictif lu dans la doc, le
  z-score contre une référence indépendante, et la situation exacte du
  premier retour de l'utilisateur (exemple collé, NQ1!, vu le week-end).
  **Piège du banc** : PineTS traite une bougie postérieure à l'horloge du
  système comme du temps réel non confirmé — `barstate.isconfirmed` faux,
  toute la logique de l'indicateur muette, sans erreur. Un exemple daté du
  lendemain du jour où l'on lance le banc ne trace donc rien : dater les
  scénarios dans le passé.
- `docs/consigne-lou-alpz.md` — la consigne à donner au bot de relevés
  (« Lou », « grok bot » pour l'utilisateur) : ce qu'on lui envoie à chaque
  relevé, le format, la correspondance des noms Gexbot (Call Wall = Major
  Positive Gamma → CW, Put Wall = Major Negative Gamma → PS, Zero Gamma →
  GF), `/flip` d'abord parce que c'est un tableau chiffré, un seul bloc R par
  échéance et par créneau (sinon la règle du doublon d'échéance en écarte
  un). Son exemple est le scénario P du banc. PineTS écrit une couleur tantôt
  `rgb(r, g, b)`, tantôt `#RRGGBB` : lire les deux. Trois écarts de PineTS sont
  contournés dans le code sans effet pour TradingView (voir son README). Ce
  n'est pas le compilateur TradingView : la vérification finale reste
  l'éditeur Pine de l'utilisateur. Hors des tests Python.
- Documentation Pine officielle : `www.tradingview.com` est joignable depuis
  l'environnement « X » (ajouté le 7 novembre 2026). Les pages du manuel
  (`/pine-script-docs/...`) se lisent avec `curl --compressed` et une
  conversion HTML → texte ; le manuel de référence (`/pine-script-reference/v6/`)
  est une application JavaScript et ne se lit pas ainsi.
- Ces quatre fichiers ne participent ni aux documents ni aux tests : ils n'ont
  pas de loi nulle et n'en revendiquent aucune. **La version déployée sur le
  graphique peut donc diverger de celle du dépôt sans que rien ne le
  signale** — c'est arrivé sur `alp0.pine`, dont le panneau imprimait une
  chaîne absente du fichier. Resynchroniser avant de tirer une conclusion.
