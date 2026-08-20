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
    scores={"a1": 5, "a2": 5, "a3": 4, "a4": 3,
            "b1": 1, "b2": 5, "b3": 4, "b4": 4,
            "c1": 4, "c2": 5, "c3": 5, "c4": 5},
    evidence={
        "a1": "Le critère maître d'ALP-1 est conservé sans modification ; la "
              "géométrie à barrière unique ajoute deux formes fermées, vérifiées "
              "contre quadrature.",
        "a2": "Même dispositif : gabarit de prose, chiffres injectés par le noyau, "
              "tests unitaires.",
        "a3": "σ₁ est déduit de la dispersion de séance au lieu d'être posé à côté "
              "d'elle ; les seuils sont donnés sur une grille de stops et de "
              "volatilités plutôt qu'à un point.",
        "a4": "Même diffusion, mêmes angles morts : sauts, saisonnalité, "
              "hétéroscédasticité. Le stop large et la sortie à l'heure y sont moins "
              "sensibles que des barrières serrées, sans y échapper.",
        "b1": "Aucune mesure conduite ici : le document reprend des résultats "
              "publiés par des tiers, sans les ré-estimer. C'est la limite "
              "principale du document.",
        "b2": "L'effet retenu est documenté sur 60 futures et 46 ans, répliqué sur "
              "actions et sur ES/NQ, et son mécanisme — la couverture gamma — fait "
              "l'objet d'une littérature séparée. Les magnitudes publiées sont "
              "reprises et comparées aux seuils calculés ici.",
        "b3": "Le candidat est nommé, daté, chiffré en points de base par trade, et "
              "confronté au seuil de friction. Il n'est pas ré-estimé sur données "
              "propres, d'où la réserve.",
        "b4": "Budget de configurations posé à trois, seuil déflaté calculé, et les "
              "variantes optimisées de la littérature sont écartées comme telles.",
        "c1": "c/L tombe à 1,6 % et IR* à 0,009 : la marge entre le seuil et la "
              "dérive documentée est d'un facteur dix, contre un facteur inconnu "
              "auparavant.",
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
