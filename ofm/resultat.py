"""Le résultat d'une hypothèse du registre, tel que la synthèse le lit."""

from __future__ import annotations

from dataclasses import dataclass, field


def entier(v: float) -> str:
    """Un effectif à la française : espace fine insécable entre les milliers."""
    return f"{v:,.0f}".replace(",", "\u202f")


@dataclass
class Resultat:
    id: str
    effet: float                     # dans l'unité de `unite`
    ic: tuple[float, float]          # intervalle à 95 %
    p: float                         # bilatéral
    n: int                           # observations (ou grappes, voir `methode`)
    unite: str                       # « pt », « × », « r »…
    lecture: str                     # la phrase chiffrée, calculée
    methode: str                     # la loi nulle ou le modèle
    base: float | None = None        # taux de référence, pour le budget de test
    relatif: float | None = None     # effet relatif à la base, pour le budget
    extra: dict = field(default_factory=dict)
