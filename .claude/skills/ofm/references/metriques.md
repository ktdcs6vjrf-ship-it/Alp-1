# Métriques, prix et PPV

## 1. Les formules

Notations sur une période (en général le mois) :

- `R_brut` : ce que paient les fans (abonnements + PPV + pourboires).
- **Part plateforme** : OnlyFans prélève 20 % ; la créatrice reçoit `R_net = 0,8 × R_brut`.
  Vérifie le taux de Fansly ou Fanvue avant de calculer pour elles.
- **Commission agence** `c` (souvent entre 30 et 50 % de `R_net`, selon ce que l'agence
  apporte) : `revenu_agence = c × R_net`, `revenu_créatrice = (1 − c) × R_net`.
- **Marge agence** = `revenu_agence − salaires chatteurs − outils − publicité`.
- **ARPPU** (revenu par fan payant) = `R_brut / fans_payants`.
- **Part PPV** = `R_PPV / R_brut`. Une page qui vit de l'abonnement seul plafonne vite.
- **Renouvellement** = `fans abonnés en début de mois encore abonnés en fin de mois / fans
  abonnés en début de mois`. C'est le chiffre qui dit si la page a de la valeur.
- **Valeur d'un fan** (LTV) ≈ `ARPPU mensuel / (1 − renouvellement)`.
- **Coût d'acquisition** (CAC) = `dépense du canal / nouveaux abonnés venus du canal`.
  Un canal se garde si `LTV × 0,8 × c > CAC` (ce que l'agence touche d'un fan doit dépasser
  ce qu'il coûte à acquérir).
- **Conversion du lien** = `nouveaux abonnés / clics sur le lien de suivi`.

Calcule toujours depuis les exports, jamais depuis des souvenirs. Si une donnée manque,
dis laquelle et demande-la.

## 2. Prix

- **Page payante** : l'abonnement filtre et rapporte dès le premier jour. Prix d'appel
  courant entre 5 et 15 $ ; promotions à durée limitée pour le lancement.
- **Page gratuite** : plus d'abonnés, tout le revenu vient des PPV et des messages. Plus de
  travail de chat. Souvent tenue *en plus* de la page payante, comme entonnoir.
- **Débutant** : commencer par une seule page payante, avec une promotion de lancement.
- **Bundles** : 3, 6, 12 mois avec remise croissante ; ils améliorent le renouvellement.

## 3. PPV — l'échelle

Une échelle de prix croissants plutôt qu'un prix unique : un premier contenu peu cher pour
faire franchir le premier achat, puis des paliers plus chers pour ceux qui ont déjà acheté.
Mesure par palier : taux d'ouverture, taux d'achat, revenu. Retire un palier qui ne vend pas
plutôt que de baisser tous les prix.

Messages groupés : au plus une ou deux fois par jour, segmentés (nouveaux, acheteurs,
inactifs). Trop de messages font chuter le renouvellement : surveille-le après chaque
changement de rythme.

## 4. Le tableau de bord hebdomadaire

Un tableur, une ligne par semaine et par créatrice :

| Semaine | Nouveaux abonnés | Abonnés actifs | Renouvellement | R_brut | Part PPV | ARPPU | Clics lien | Conversion | Dépense pub | Marge agence |
|---|---|---|---|---|---|---|---|---|---|---|

Lis-le avec l'utilisateur chaque semaine : quel chiffre a bougé, pourquoi, quelle action.
