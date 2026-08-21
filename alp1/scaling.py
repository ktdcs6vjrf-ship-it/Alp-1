"""Cohérence de l'exposant d'échelle, et géométrie robuste à son incertitude.

Ce module corrige une incohérence interne du document, et en tire une décision
de conception.

**L'incohérence.** La calibration pose une dispersion de séance et en déduit la
volatilité par minute par ``σ₁ = D/√T``. Ce ``√`` est l'exposant d'échelle
d'un brownien, H = ½ ; il est posé, jamais mesuré. Ailleurs, le document
retient H = 0,65 pour discuter de l'atteignabilité des targets. Les deux
énoncés ne peuvent pas être vrais ensemble : ou bien le prix diffuse en racine
du temps, et alors la calibration est bonne mais la persistance invoquée
n'existe pas ; ou bien il diffuse en t^H avec H > ½, et alors c'est ``σ₁`` qui
est faux, et avec lui la bande de bruit, le stop, l'exposition et le seuil.

**La correction.** Une seule calibration est cohérente avec un exposant donné :
``σ₁(H) = D/T^H``. Tout le reste s'en déduit. Ce module refait la chaîne
complète pour un H quelconque et montre dans quel sens la conclusion bouge.

Le résultat va contre l'intuition qui a motivé le recours à H > ½. Une
persistance plus forte n'aide pas : elle rend le stop plus fréquemment touché
et le seuil d'entrée plus exigeant. L'atteignabilité du target, seul canal par
lequel le document faisait jouer H, est négligeable devant ces deux effets,
parce que le target n'est presque jamais atteint.

**La réserve de méthode.** Le premier passage d'un processus auto-similaire à
exposant H ≠ ½ n'a pas de forme fermée. On utilise ici le changement de temps
``t → t^(2H)`` : il rend la loi marginale **exacte** — le processus a bien la
dispersion ``σ₁t^H`` à toute date — mais il ignore que les incréments d'un
mouvement brownien fractionnaire sont corrélés, alors que ceux du brownien
changé de temps ne le sont pas. La probabilité d'arrêt en est sous-estimée
pour H > ½, puisque la corrélation positive favorise les excursions longues.
Les écarts rapportés ici sont donc des **bornes basses** de l'effet, ce qui
suffit à la conclusion : l'effet joue déjà contre la stratégie sous sa forme
la plus favorable.

**Le mécanisme, et pourquoi la question reste ouverte.** Le document montre
déjà que le régime de gamma ne peut pas produire H = 0,65 : il y faudrait un
gamma net d'un ordre de grandeur au-dessus de l'observable. Le candidat
suivant de la littérature ne fait pas mieux. Le fractionnement des ordres
institutionnels engendre bien une mémoire longue du flux signé — c'est le
résultat de Lillo, Mike et Farmer (2005), et il est solidement établi — mais
Bouchaud, Gefen, Potters et Wyart (2004) montrent que l'impact décroît selon
un noyau dont l'exposant est précisément celui qui **restaure** la
diffusivité : la mémoire du flux est compensée, et le prix reste à H ≈ ½ par
construction. Le mécanisme le mieux documenté de persistance du flux est donc
aussi celui qui garantit l'absence de persistance du prix.

Aucun mécanisme documenté ne soutient donc H = 0,65. Deux conséquences sont
inscrites ici : la géométrie doit être choisie robuste à H plutôt qu'optimale
en un point, et le Test 1 du protocole — la mesure de H — est bien à sa place
en tête de séquence, puisqu'il décide de la calibration entière et non du seul
target.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .momentum import expected_exposure, prob_stop

#: Exposant d'un prix sans mémoire. La calibration du document le suppose.
HURST_MARTINGALE = 0.5

#: Exposant retenu par le document pour discuter des targets.
HURST_ASSUMED = 0.65

#: Boîte de plausibilité de l'exposant. La borne basse est la martingale, que
#: la théorie de l'efficience impose et que le noyau d'impact restaure ; la
#: borne haute est la valeur retenue par le document. Aucune valeur inférieure
#: à ½ n'est explorée : un prix anti-persistant rendrait la géométrie plus
#: facile, et l'exclure est le choix conservateur.
HURST_LO, HURST_HI = 0.50, 0.65


@dataclass(frozen=True)
class Scaled:
    """La chaîne de calibration complète, à exposant d'échelle imposé."""

    hurst: float
    session_dispersion: float
    session_min: float
    entry_min: float
    friction: float

    sigma_1min: float
    band: float
    horizon: float
    p_stop: float
    exposure: float
    mu_star: float
    ir_star: float

    @property
    def mu_star_per_hour(self) -> float:
        return self.mu_star * 60.0

    def net_points(self, edge_points: float) -> float:
        """Espérance nette µ·E[τ] − c, la dérive étant donnée en points captés."""
        return edge_points - self.friction

    def signal_ir(self, edge_points: float) -> float:
        """Ratio d'information que le signal doit avoir pour capter `edge_points`."""
        denom = self.sigma_1min * (self.exposure ** self.hurst)
        return edge_points / denom if denom > 0 else math.inf

    @property
    def margin(self) -> float:
        """Rapport du IR du signal au IR requis. Sans unité."""
        return math.inf if self.ir_star <= 0 else 1.0 / self.ir_star


def calibrate(hurst: float,
              session_dispersion: float = 60.0,
              session_min: float = 390.0,
              entry_min: float = 90.0,
              friction: float = 0.33) -> Scaled:
    """Refait la chaîne de calibration sous l'exposant `hurst`.

    Les quatre entrées sont celles du document. Rien n'est ajouté : seul le
    ``√`` de ``sigma_from_session`` est remplacé par ``t^H``, et la propagation
    en découle.

        σ₁ = D/T^H
        L  = σ₁·t_e^H·√(2/π)          (bande de bruit à l'heure d'entrée)
        T' = (T − t_e)^(2H)           (horizon en temps effectif)
        E[τ∧T] = E_brownien(L, T', σ₁)^(1/(2H))   (retour en minutes d'horloge)
        µ* = c/E[τ∧T]
        IR* = c/(σ₁·E[τ∧T]^H)

    À H = ½ le changement de temps est l'identité, et la fonction rend
    exactement les nombres du document.
    """
    if not 0.0 < hurst < 1.0:
        raise ValueError("hurst doit être dans ]0, 1[")
    if session_dispersion <= 0 or session_min <= 0:
        raise ValueError("dispersion et durée de séance doivent être > 0")
    if not 0.0 < entry_min < session_min:
        raise ValueError("entry_min doit être dans ]0, session_min[")

    sigma = session_dispersion / (session_min ** hurst)
    band = sigma * (entry_min ** hurst) * math.sqrt(2.0 / math.pi)
    remaining = session_min - entry_min
    t_eff = remaining ** (2.0 * hurst)

    p = prob_stop(band, t_eff, sigma)
    exposure = expected_exposure(band, t_eff, sigma) ** (1.0 / (2.0 * hurst))

    mu_star = friction / exposure if exposure > 0 else math.inf
    denom = sigma * (exposure ** hurst)
    ir_star = friction / denom if denom > 0 else math.inf

    return Scaled(hurst=hurst, session_dispersion=session_dispersion,
                  session_min=session_min, entry_min=entry_min,
                  friction=friction, sigma_1min=sigma, band=band,
                  horizon=remaining, p_stop=p, exposure=exposure,
                  mu_star=mu_star, ir_star=ir_star)


def sensitivity(lo: float = HURST_LO, hi: float = HURST_HI,
                n: int = 5, **kw) -> list[Scaled]:
    """La chaîne recalculée en `n` points de la boîte d'exposant."""
    if n < 2:
        raise ValueError("n doit être ≥ 2")
    return [calibrate(lo + (hi - lo) * i / (n - 1), **kw) for i in range(n)]


def worst_case(lo: float = HURST_LO, hi: float = HURST_HI,
               n: int = 9, **kw) -> Scaled:
    """Le point de la boîte d'exposant où le seuil requis est le plus élevé.

    C'est la calibration sous laquelle la géométrie doit rester rentable pour
    que la conclusion ne dépende pas d'un exposant non mesuré.
    """
    return max(sensitivity(lo, hi, n, **kw), key=lambda s: s.ir_star)


def robust_entry(lo: float = HURST_LO, hi: float = HURST_HI, n: int = 9,
                 entries: tuple[float, ...] = (30.0, 60.0, 90.0, 120.0, 180.0),
                 **kw) -> list[tuple[float, float, float, float]]:
    """Heure d'entrée choisie au pire cas sur la boîte d'exposant.

    Retourne, par heure d'entrée : (heure, exposition au pire cas en minutes,
    dérive requise µ* au pire cas en points par heure, IR* au pire cas).
    L'heure retenue est celle qui minimise la dérive requise au pire cas — la
    seule qui ne parie pas sur une valeur de H que personne n'a mesurée.

    Deux effets s'opposent quand l'entrée est retardée. La bande de bruit
    s'élargit, donc le stop s'éloigne et l'exposition s'allonge ; mais la
    séance restante raccourcit, donc l'exposition plafonne. L'optimum est
    intérieur, et il ne coïncide pas avec l'heure retenue par le document.
    """
    out = []
    for t in entries:
        w = worst_case(lo, hi, n, entry_min=t, **kw)
        out.append((t, w.exposure, w.mu_star_per_hour, w.ir_star))
    return out


def coherence_gap(hurst: float = HURST_ASSUMED, **kw) -> tuple[float, float, float]:
    """Écart entre la calibration du document et sa version cohérente.

    Retourne (IR* à H = ½, IR* à H, rapport). Le rapport est le facteur par
    lequel le document sous-estime le seuil qu'il impose au signal, s'il faut
    prendre au sérieux l'exposant qu'il invoque par ailleurs.
    """
    a = calibrate(HURST_MARTINGALE, **kw)
    b = calibrate(hurst, **kw)
    return a.ir_star, b.ir_star, (b.ir_star / a.ir_star if a.ir_star else math.inf)
