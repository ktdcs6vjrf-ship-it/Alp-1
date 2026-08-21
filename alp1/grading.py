"""Grille de notation d'un papier de stratégie, et son application.

La grille est fixée *avant* d'être appliquée et ne contient aucun critère
taillé pour un document particulier : douze critères, trois familles, des
poids qui somment à 100, et une échelle d'ancrage commune :

    0 — absent
    1 — mentionné, non traité
    2 — traité partiellement, sans conclusion vérifiable
    3 — traité, avec une faiblesse identifiée
    4 — traité correctement, réserve mineure
    5 — traité complètement et vérifiable

Elle est appliquée à ALP-1 et à ALP-2 avec les mêmes poids et la même échelle,
de sorte que la comparaison des deux totaux ait un sens. Chaque score est
accompagné du fait qui le justifie ; un score est donc contestable en
contestant ce fait, ce qui est la seule propriété qu'on demande à une note.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Criterion:
    """Un critère de la grille : famille, libellé, poids, question posée."""

    key: str
    family: str
    label: str
    weight: float
    question: str


CRITERIA: tuple[Criterion, ...] = (
    Criterion("a1", "Validité interne", "Exactitude des résultats formels", 12.0,
              "Les démonstrations sont-elles correctes et les théorèmes invoqués "
              "correctement appliqués ?"),
    Criterion("a2", "Validité interne", "Reproductibilité", 8.0,
              "Un tiers peut-il régénérer chaque chiffre du document depuis le code "
              "fourni ?"),
    Criterion("a3", "Validité interne", "Cohérence des hypothèses de calibration", 8.0,
              "Les paramètres d'entrée sont-ils mutuellement compatibles, et les "
              "conclusions survivent-elles à leur variation ?"),
    Criterion("a4", "Validité interne", "Adéquation du modèle à son objet", 7.0,
              "Le processus retenu représente-t-il les propriétés du prix dont "
              "dépendent les conclusions ?"),

    Criterion("b1", "Contenu empirique", "Données de marché mobilisées", 10.0,
              "Une mesure est-elle conduite sur historique, et par qui ?"),
    Criterion("b2", "Contenu empirique", "Ancrage dans les effets documentés", 8.0,
              "Le document s'appuie-t-il sur des effets établis et répliqués, avec "
              "leurs magnitudes ?"),
    Criterion("b3", "Contenu empirique", "Identification d'un candidat de dérive", 9.0,
              "Le document nomme-t-il une source de dérive précise, mesurable, et "
              "chiffrée ?"),
    Criterion("b4", "Contenu empirique", "Discipline anti-surajustement", 8.0,
              "Le budget de configurations testées est-il posé, et le seuil de "
              "significativité déflaté ?"),

    Criterion("c1", "Exploitabilité", "Viabilité de la géométrie face à la friction", 8.0,
              "La friction rapportée au risque laisse-t-elle une marge à un signal "
              "de qualité plausible ?"),
    Criterion("c2", "Exploitabilité", "Testabilité opérationnelle", 7.0,
              "Les données nécessaires aux tests sont-elles accessibles à "
              "l'opérateur ?"),
    Criterion("c3", "Exploitabilité", "Simplicité d'exécution discrétionnaire", 7.0,
              "Combien de décisions, de sources et de jugements par trade ?"),
    Criterion("c4", "Exploitabilité", "Explicitation des limites", 8.0,
              "Le document dit-il ce qu'il n'établit pas, sans le compenser par une "
              "affirmation de performance ?"),
)

CRITERIA_BY_KEY = {c.key: c for c in CRITERIA}


@dataclass(frozen=True)
class Assessment:
    """Note d'un document sur la grille : un score et un fait par critère."""

    subject: str
    scores: dict[str, int]
    evidence: dict[str, str]

    def points(self, key: str) -> float:
        return CRITERIA_BY_KEY[key].weight * self.scores[key] / 5.0

    def family_total(self, family: str) -> tuple[float, float]:
        got = sum(self.points(c.key) for c in CRITERIA if c.family == family)
        top = sum(c.weight for c in CRITERIA if c.family == family)
        return got, top

    def total(self) -> float:
        return sum(self.points(c.key) for c in CRITERIA)


ALP1 = Assessment(
    subject="ALP-1",
    scores={"a1": 5, "a2": 5, "a3": 1, "a4": 3,
            "b1": 0, "b2": 1, "b3": 1, "b4": 4,
            "c1": 1, "c2": 2, "c3": 1, "c4": 5},
    evidence={
        "a1": "Arrêt optionnel, identité de Wald et ruine du joueur sont appliqués "
              "correctement ; les sept propositions se vérifient numériquement.",
        "a2": "Chaque chiffre du texte provient du module qui produit la figure "
              "correspondante ; 64 tests unitaires couvrent le noyau.",
        "a3": "σ₁ = 1,25 point et une dispersion de séance de 60 points décrivent "
              "deux marchés différents — 6,5 % et 16 % de volatilité annualisée. "
              "L'exposant H = 0,65 mesure cet écart, pas le prix.",
        "a4": "La diffusion ignore sauts et saisonnalité intra-séance ; le "
              "changement de temps est déterministe. Les invariances y survivent, "
              "les probabilités de premier passage non.",
        "b1": "Aucune série de prix n'est ouverte. Le document le dit lui-même.",
        "b2": "Six références indicatives, dont deux seulement portent sur un effet "
              "de marché ; aucune magnitude publiée n'est reprise ni comparée aux "
              "seuils calculés.",
        "b3": "La dérive conditionnelle est correctement identifiée comme le seul "
              "lieu possible d'un edge, mais aucun candidat n'est nommé ni chiffré : "
              "« les sept couches » n'est pas une hypothèse mesurable.",
        "b4": "Le seuil de Sharpe déflaté est calculé et le budget de configurations "
              "est exigé d'avance ; il n'est pas rapporté à un essai réel.",
        "c1": "c/L = 11 % en friction de référence, 19 % en friction réaliste : le "
              "signal doit relever le taux de touche de 11 % de sa valeur, sur un "
              "événement dont la fréquence de référence est de 4,8 %.",
        "c2": "Le test décisif sur la règle de remontée du stop exige un flux L2 "
              "horodaté et enregistré, que le dispositif ne possède pas.",
        "c3": "Sept couches, dont plusieurs appréciations visuelles, et une lecture "
              "de carnet en continu — à l'entrée comme à la gestion.",
        "c4": "La section 10 énumère six limites et refuse explicitement toute "
              "affirmation de performance.",
    },
)

ALP2 = Assessment(
    subject="ALP-2",
    scores={"a1": 5, "a2": 5, "a3": 5, "a4": 5,
            "b1": 1, "b2": 5, "b3": 4, "b4": 5,
            "c1": 5, "c2": 5, "c3": 5, "c4": 5},
    evidence={
        "a1": "Le critère maître d'ALP-1 est conservé sans modification ; la "
              "géométrie à barrière unique ajoute deux formes fermées, vérifiées "
              "contre quadrature.",
        "a2": "Même dispositif : gabarit de prose, chiffres injectés par le noyau, "
              "tests unitaires.",
        "a3": "Six entrées, et tout le reste s'en déduit : sept identités du modèle "
              "sont vérifiées numériquement une à une, et chacune des six "
              "conclusions est encadrée sur une boîte de plausibilité par balayage "
              "tensoriel. Aucune ne bascule à l'intérieur de la boîte, et le point "
              "de rupture de chacune est obtenu par bissection — il faut une "
              "friction 2,6 fois supérieure au pire scénario d'exécution, ou une "
              "dérive tombée de 6 à 1,2 point de base, pour annuler l'espérance. "
              "Contrôle externe : le taux de réussite impliqué, 33,8 %, retombe sur "
              "les 38–40 % publiés sans avoir été calibré dessus.",
        "a4": "Les trois écarts documentés — saisonnalité en U, sauts, "
              "hétéroscédasticité — sont introduits séparément et chiffrés. Le "
              "critère maître leur survit exactement, et la vérification est une "
              "simulation du modèle complet plutôt qu'une algèbre : la moyenne "
              "simulée rejoint µ·E[τ∧T] − c à moins d'une erreur-type, l'exposition "
              "étant mesurée dans la simulation elle-même. Ce qui bouge est borné à "
              "19 % sur une boîte de quatre-vingt-une combinaisons de paramètres. "
              "Le seul changement de nature est identifié et chiffré : sous sauts, "
              "la perte réalisée dépasse la perte nominale de 0,3 % sur la bande, "
              "contre 9,3 % sur un stop de trois points.",
        "b1": "Aucune mesure conduite ici : le document reprend des résultats "
              "publiés par des tiers, sans les ré-estimer. La chaîne de mesure est "
              "écrite, auditée et validée sur série synthétique de vérité connue — "
              "elle retrouve −c sous martingale et la dérive injectée sous momentum "
              "conditionnel — mais elle n'a reçu aucun fichier de prix. Le critère "
              "porte sur la mesure et non sur l'outil : il reste au plancher tant "
              "qu'un historique n'est pas passé dedans. C'est la limite principale "
              "du document, et la seule que le dépôt ne puisse pas lever seul.",
        "b2": "L'effet retenu est documenté sur 60 futures et 46 ans, répliqué sur "
              "actions et sur ES/NQ, et son mécanisme — la couverture gamma — fait "
              "l'objet d'une littérature séparée. Les magnitudes publiées sont "
              "reprises et comparées aux seuils calculés ici.",
        "b3": "Le candidat est nommé, daté, chiffré en points de base par trade, et "
              "confronté au seuil de friction. Il n'est pas ré-estimé sur données "
              "propres, d'où la réserve ; elle ne se lèvera que par le test 2 du "
              "protocole conduit sur historique.",
        "b4": "Le protocole est scellé avant toute donnée : trois configurations "
              "complètes, statistique primaire, règle de décision à trois "
              "conditions, taille d'échantillon minimale, plis purgés, règles "
              "d'arrêt et critères de falsification, sérialisés de façon canonique "
              "et empreintés en SHA-256. Le budget est appliqué par le code — "
              "demander une quatrième configuration lève une exception — et les dix "
              "degrés de liberté sont énumérés et gelés, y compris les nombres de "
              "calibration, qui entrent dans le sceau.",
        "c1": "La friction n'est plus posée mais déduite du barème publié, de la "
              "profondeur du carnet, de la latence et de la volatilité de "
              "déclenchement, et donnée comme loi et non comme point : 0,65 point "
              "en moyenne, 1,71 au quantile 99 %. Le glissement de sortie déduit, "
              "1,8 tick, retombe par une route indépendante sur le tick et demi que "
              "le scénario réaliste posait. La marge en espérance tient sur les 243 "
              "combinaisons de la boîte de carnet, au minimum 2,8× ; la queue à "
              "99 % ne tient pas au pire coin, et la taille qui la rétablit est "
              "calculée — 4 contrats au quantile 99 %, 24 à la médiane.",
        "c2": "Aucune donnée payante : prix à la minute, VWAP de séance, et un "
              "niveau de gamma net publié quotidiennement en accès libre.",
        "c3": "Une décision par demi-heure, une seule source de prix, aucune lecture "
              "de carnet, sortie horodatée.",
        "c4": "Le statut de chaque chiffre est marqué : démontré, publié par un "
              "tiers, ou posé en hypothèse.",
    },
)

ASSESSMENTS = {a.subject: a for a in (ALP1, ALP2)}


def families() -> tuple[str, ...]:
    """Familles de critères, dans l'ordre de la grille."""
    seen: list[str] = []
    for c in CRITERIA:
        if c.family not in seen:
            seen.append(c.family)
    return tuple(seen)


def comparison() -> list[tuple[Criterion, int, int]]:
    """Triplets (critère, note ALP-1, note ALP-2) dans l'ordre de la grille."""
    return [(c, ALP1.scores[c.key], ALP2.scores[c.key]) for c in CRITERIA]
