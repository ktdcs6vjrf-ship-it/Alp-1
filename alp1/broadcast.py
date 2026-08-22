"""La couche témoin : ce qu'un signal diffusé en direct peut valoir.

Un opérateur diffuse ses entrées en direct — plateau vidéo, position visible à
l'écran, commentaire au moment de l'exécution. Un spectateur veut savoir si
ce flux porte une information exploitable à l'instant `t`, et le dépôt possède
déjà tout ce qu'il faut pour répondre sans ouvrir une seule série de prix. La
question n'est pas neuve : c'est celle du carnet d'ordres, posée sur un canal
plus lent et plus bruité.

Le module répond en quatre temps, et chacun produit une borne.

**La latence factorise exactement.** Un signal a une demi-vie ; un direct a un
délai — encodage, mémoire tampon du diffuseur, réseau de distribution, temps
de réaction humain. La dérive captée par un receveur qui entre avec un retard
`Δ` et reste exposé `τ` vaut

    µ̄ = µ₀ · 2^(−Δ/h) · (T_c/τ)·(1 − 2^(−τ/h))

soit exactement la dérive captée sans latence, multipliée par `2^(−Δ/h)`. Le
retard ne déforme pas le profil : il l'atténue d'un facteur qui ne dépend que
du rapport du délai à la demi-vie. D'où la **frontière de tolérance** : un
signal dont la demi-vie est inférieure à `h* = Δ·ln 2 / ln(µ/µ*)` ne finance
pas l'aller-retour du receveur, quelle que soit sa qualité chez l'émetteur.

**Le classement a une loi nulle, et elle est sévère.** Chercher « le bon
diffuseur » parmi `K` candidats est une sélection sur `K` configurations. Le
meilleur de `K` diffuseurs sans aucun talent affiche en espérance un Sharpe de
`√(2 ln K / N)` : à `K` = 100 et 300 appels, cela vaut 0,124 par appel — bien
au-dessus de ce qu'un vrai talent modeste produirait. Le dépôt possède déjà
l'instrument (`overfit.expected_max_sharpe`) ; il suffit de l'appliquer à des
personnes plutôt qu'à des paramètres.

**Un historique reconstitué n'est pas un échantillon.** Un diffuseur qui
efface une fraction `d` de ses appels perdants affiche

    p_obs = p₀ / (p₀ + (1 − p₀)(1 − d))

et la relation s'inverse : à taux affiché donné, on calcule la fraction
d'effacement qui **suffit à tout expliquer**. Elle est petite. C'est pourquoi
la seule collecte recevable est prospective et horodatée à la réception.

**Il reste une lecture recevable, et ce n'est pas celle qu'on cherchait.** Ce
qu'un direct mesure de façon fiable n'est pas une prévision de prix mais une
**attention datée** : combien de participants regardent le même niveau au même
instant. Le cadre du document range cette grandeur du côté de la capacité et
de la friction, non du côté de la dérive — et Barber, Huang, Odean et Schwarz
(2022) documentent que les épisodes d'attention retail extrême sont suivis de
rendements négatifs, non positifs. Le témoin est un instrument de foule, pas
un instrument de prévision.

Références employées, et leur statut :

- Kakhbod, Kazempour, Livdan et Schürhoff (2023), *Finfluencers*, SFI
  Research Paper 23-30 — taux de base publiés, employés ici comme prior.
- Barber, Huang, Odean et Schwarz (2022), *Attention-Induced Trading and
  Returns*, Journal of Finance 77(6) — direction seule, aucun chiffre repris.
- Bailey et López de Prado, via `alp1.overfit` — loi nulle du classement.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

from .costs import _norm_ppf, norm_cdf
from .overfit import expected_max_sharpe

_LN2 = math.log(2.0)


# --- Ce qui est posé, et ce qui est publié ----------------------------------

#: Délai total entre l'exécution du diffuseur et celle du receveur, en
#: secondes. **Posé, encadré.** Trois postes s'additionnent : l'encodage et la
#: mémoire tampon de la diffusion en direct, la distribution jusqu'au
#: spectateur, et le temps de réaction humain. La borne basse suppose une
#: diffusion à faible latence et un receveur déjà armé ; la borne haute, une
#: diffusion ordinaire et une décision à prendre. Aucune de ces valeurs n'est
#: mesurée ici : elles encadrent, elles ne calibrent pas.
LATENCY_BOX_S = (3.0, 10.0, 30.0)

#: Demi-vies de référence des signaux, en secondes. La première est celle que
#: le document retient pour un signal de flux (trois secondes) ; les suivantes
#: correspondent à un motif de barre d'une minute, à un motif de séance, et à
#: une thèse tenue à la journée.
HALF_LIFE_GRID_S = (3.0, 60.0, 1800.0, 23400.0)

#: Taux de base publiés par Kakhbod et al. (2023) sur un échantillon de
#: diffuseurs financiers : part de talent, part sans talent, part de talent
#: **négatif**. La somme vaut un. Ces trois nombres ne sont pas des mesures du
#: dépôt ; ils servent de loi a priori, et rien d'autre.
FINFLUENCER_PRIOR = {"talent": 0.28, "neutre": 0.16, "antitalent": 0.56}

#: Rendement anormal mensuel publié pour chacun des trois types, en fraction.
#: Le type neutre est à zéro par définition du classement d'origine.
FINFLUENCER_ALPHA = {"talent": 0.026, "neutre": 0.0, "antitalent": -0.023}

#: Écart-type mensuel du rendement anormal d'un diffuseur suivi. **Posé,
#: encadré.** Il n'est pas publié par le travail cité ; les trois valeurs
#: encadrent ce qu'un portefeuille concentré de quelques titres produit. Il
#: n'entre que dans la puissance du filtre, jamais dans les taux de base.
FINFLUENCER_SD_BOX = (0.06, 0.10, 0.15)


# --- La latence, et la frontière qu'elle trace ------------------------------

def latency_factor(delay_s: float, half_life_s: float) -> float:
    """Part de l'information qui survit à un délai de diffusion.

    Vaut ``2^(−Δ/h)``. C'est le facteur exact par lequel la latence multiplie
    la dérive captée : il se compose avec la décroissance sur l'exposition
    sans terme croisé, parce que l'exponentielle est sans mémoire.
    """
    if half_life_s <= 0.0:
        raise ValueError("half_life_s doit être > 0")
    if delay_s < 0.0:
        raise ValueError("delay_s doit être ≥ 0")
    return 2.0 ** (-delay_s / half_life_s)


def usable_drift(instant_drift: float, half_life_s: float,
                 exposure_min: float, delay_s: float) -> float:
    """Dérive moyenne captée par un receveur en retard de `delay_s`.

    Reprend `orderflow.captured_drift` — moyenne de la dérive instantanée sur
    la fenêtre d'exposition — et lui applique le facteur de latence. L'unité
    de `instant_drift` est libre ; celle du résultat est la même.
    """
    if exposure_min <= 0.0:
        raise ValueError("exposure_min doit être > 0")
    h_min = half_life_s / 60.0
    tau_c = h_min / _LN2
    integre = instant_drift * (tau_c / exposure_min) * (
        1.0 - math.exp(-exposure_min / tau_c))
    return integre * latency_factor(delay_s, half_life_s)


def required_emitter_drift(breakeven_drift: float, delay_s: float,
                           half_life_s: float) -> float:
    """Dérive que l'émetteur doit produire pour que le receveur soit à zéro.

    Vaut ``µ*·2^(Δ/h)``. Le facteur d'inflation ne dépend d'aucune propriété
    du marché : c'est un rapport de deux durées.
    """
    return breakeven_drift / latency_factor(delay_s, half_life_s)


def min_half_life(delay_s: float, drift_ratio: float) -> float:
    """Demi-vie minimale d'un signal recopiable, en secondes.

    Un receveur qui subit `Δ` et dont l'émetteur produit `µ = ratio · µ*` ne
    reste au-dessus de zéro que si la demi-vie du signal vérifie

        h ≥ Δ · ln 2 / ln(ratio).

    La frontière diverge quand le ratio tend vers un : plus l'émetteur est
    près du seuil, plus son signal doit être lent pour survivre au trajet.
    Rendue infinie si l'émetteur n'est pas strictement au-dessus du seuil.
    """
    if delay_s < 0.0:
        raise ValueError("delay_s doit être ≥ 0")
    if drift_ratio <= 1.0:
        return math.inf
    return delay_s * _LN2 / math.log(drift_ratio)


def tolerated_delay(half_life_s: float, drift_ratio: float) -> float:
    """Délai maximal supportable, en secondes. Réciproque de `min_half_life`."""
    if drift_ratio <= 1.0:
        return 0.0
    return half_life_s * math.log(drift_ratio) / _LN2


# --- L'historique reconstitué, et ce qu'il suffit d'effacer -----------------

def observed_hit_rate(p_null: float, deleted: float) -> float:
    """Taux de réussite affiché quand une fraction `deleted` des pertes saute.

    Les gains sont tous montrés, une part des pertes disparaît : la fréquence
    affichée est ``p₀ / (p₀ + (1 − p₀)(1 − d))``. Aucune intention n'est
    supposée — un oubli, un direct interrompu ou une sélection de ce qui
    mérite un récapitulatif produisent la même arithmétique.
    """
    if not 0.0 <= p_null <= 1.0:
        raise ValueError("p_null doit être dans [0, 1]")
    if not 0.0 <= deleted < 1.0:
        raise ValueError("deleted doit être dans [0, 1[")
    reste = p_null + (1.0 - p_null) * (1.0 - deleted)
    return p_null / reste if reste > 0.0 else 1.0


def deletion_explaining(p_null: float, p_observed: float) -> float:
    """Fraction de pertes effacées qui reproduit exactement le taux affiché.

    Inversion de `observed_hit_rate` :

        d = 1 − p₀(1 − p_obs) / [(1 − p₀)·p_obs].

    C'est le nombre à opposer à tout historique reconstitué. S'il est petit,
    l'écart au hasard n'est pas une preuve de talent : c'est une explication
    parmi deux, et la moins coûteuse des deux.
    """
    if not 0.0 < p_observed < 1.0 or not 0.0 < p_null < 1.0:
        raise ValueError("les deux taux doivent être dans ]0, 1[")
    if p_observed <= p_null:
        return 0.0
    return 1.0 - (p_null * (1.0 - p_observed)) / ((1.0 - p_null) * p_observed)


def deletions_per_loss(p_null: float, p_observed: float) -> float:
    """Un appel perdant effacé sur combien. Lecture directe de la fraction."""
    d = deletion_explaining(p_null, p_observed)
    return math.inf if d <= 0.0 else 1.0 / d


# --- Décider sur un diffuseur, seul puis dans une foule ---------------------

def calls_to_decide(p_null: float, p_alt: float,
                    alpha: float = 0.05, power: float = 0.80) -> float:
    """Appels nécessaires pour distinguer `p_alt` de `p_null`, test unilatéral.

    Taille d'échantillon sur une proportion, variance évaluée sous chaque
    hypothèse :

        N = [z_α·√(p₀q₀) + z_β·√(p₁q₁)]² / (p₁ − p₀)².

    Rendue infinie si l'alternative ne dépasse pas la loi nulle.
    """
    if p_alt <= p_null:
        return math.inf
    za, zb = _norm_ppf(1.0 - alpha), _norm_ppf(power)
    s0 = math.sqrt(p_null * (1.0 - p_null))
    s1 = math.sqrt(p_alt * (1.0 - p_alt))
    return ((za * s0 + zb * s1) ** 2) / ((p_alt - p_null) ** 2)


def best_of_crowd(n_broadcasters: int, n_calls: int) -> float:
    """Sharpe par appel du **meilleur** de `K` diffuseurs sans aucun talent.

    L'écart-type d'un Sharpe estimé sur `N` appels vaut `1/√N` ; le maximum de
    `K` tirages indépendants suit la loi des valeurs extrêmes employée par
    `overfit.expected_max_sharpe`. Le produit des deux est la barre que le
    classement fabrique tout seul.
    """
    if n_calls < 1:
        raise ValueError("n_calls doit être ≥ 1")
    return expected_max_sharpe(max(n_broadcasters, 2), 1.0 / math.sqrt(n_calls))


def hit_rate_of_crowd(n_broadcasters: int, n_calls: int,
                      p_null: float = 0.5) -> float:
    """Le même résultat, lu en taux de réussite affiché par le meilleur.

    Un Sharpe par appel `s` sur une issue binaire correspond à un excédent de
    fréquence de ``s·√(p₀q₀)`` — la conversion est exacte à l'ordre où le
    document travaille, et elle rend le nombre lisible sans détour.
    """
    s = best_of_crowd(n_broadcasters, n_calls)
    return min(1.0, p_null + s * math.sqrt(p_null * (1.0 - p_null)))


def crowd_threshold_calls(n_broadcasters: int, lift: float,
                          p_null: float = 0.5,
                          alpha: float = 0.05, power: float = 0.80) -> float:
    """Appels par diffuseur pour qu'un talent de `lift` survive au classement.

    Le seuil de sélection est relevé par Bonferroni sur `K` diffuseurs : on
    remplace `α` par `α/K` dans la taille d'échantillon. La croissance est
    logarithmique en `K`, donc lente — et pourtant suffisante pour placer la
    décision hors de portée d'un historique de direct.
    """
    if n_broadcasters < 1:
        raise ValueError("n_broadcasters doit être ≥ 1")
    return calls_to_decide(p_null, p_null + lift,
                           alpha=alpha / n_broadcasters, power=power)


# --- Le prior publié, et ce qu'un test en fait ------------------------------

@dataclass(frozen=True)
class Posterior:
    """Ce qu'un diffuseur qui passe le filtre a de chances d'avoir du talent."""

    talent: float
    neutre: float
    antitalent: float

    @property
    def odds_anti(self) -> float:
        """Rapport de cotes du talent négatif au talent positif."""
        return math.inf if self.talent <= 0.0 else self.antitalent / self.talent


def screen_power(alpha_monthly: float, n_months: float, sd_monthly: float,
                 alpha: float = 0.05, side: str = "long") -> float:
    """Probabilité qu'un diffuseur d'alpha donné passe un filtre unilatéral.

    Test sur la moyenne de `n` mois : la statistique vaut `α√n/σ`, et le
    filtre retient au seuil `z_{1−α}`. Le côté `"short"` cherche l'écart
    **négatif** — c'est le filtre du contre-pied — et inverse donc le signe.
    """
    if n_months <= 0.0 or sd_monthly <= 0.0:
        raise ValueError("n_months et sd_monthly doivent être > 0")
    if side not in ("long", "short"):
        raise ValueError("side vaut 'long' ou 'short'")
    signe = 1.0 if side == "long" else -1.0
    z = signe * alpha_monthly * math.sqrt(n_months) / sd_monthly
    return norm_cdf(z - _norm_ppf(1.0 - alpha))


@dataclass(frozen=True)
class Screen:
    """Ce qu'un filtre retient : une loi a posteriori et un rendement."""

    posterior: Posterior
    retained: float

    @property
    def per_thousand(self) -> float:
        """Diffuseurs retenus pour mille examinés."""
        return self.retained * 1000.0


def posterior_after_screen(n_months: float = 12.0,
                           sd_monthly: float = FINFLUENCER_SD_BOX[1],
                           alpha: float = 0.05,
                           prior: dict[str, float] | None = None,
                           side: str = "long") -> Screen:
    """Loi a posteriori des trois types après un filtre, et sa part retenue.

    Rien n'est posé sur la qualité du filtre : sa puissance sur chaque type
    **se déduit** de l'alpha publié pour ce type, de la durée d'observation et
    de la dispersion encadrée. Le résultat n'est donc pas un chiffre du marché
    mais une conséquence arithmétique des taux de base publiés, et il répond à
    une question de méthode : dans quel sens chercher.

    La réponse tient en deux nombres. Le filtre inverse — chercher le talent
    négatif pour le prendre à contre-pied — a une **loi a posteriori plus
    pure** et un **rendement plus élevé**, parce qu'il vise la classe
    majoritaire. Chercher le bon diffuseur revient à chercher dans les 28 % ;
    chercher le mauvais, dans les 56 %.
    """
    p = dict(prior or FINFLUENCER_PRIOR)
    if abs(sum(p.values()) - 1.0) > 1e-9:
        raise ValueError("le prior doit sommer à un")
    vrais = {k: screen_power(FINFLUENCER_ALPHA[k], n_months, sd_monthly,
                             alpha, side) for k in p}
    masse = sum(p[k] * vrais[k] for k in p)
    if masse <= 0.0:
        raise ValueError("le filtre ne retient personne")
    post = Posterior(*(p[k] * vrais[k] / masse
                       for k in ("talent", "neutre", "antitalent")))
    return Screen(posterior=post, retained=masse)


# --- Le registre : ce qu'on collecte, et ce qu'on en refuse -----------------

#: Sources d'un appel, par ordre de recevabilité décroissante.
SOURCES = ("direct", "recapitulatif")


@dataclass(frozen=True)
class Call:
    """Un appel diffusé, horodaté **à la réception** et non à l'émission.

    `ts` est un temps Unix en secondes. `side` vaut +1 pour un achat, −1 pour
    une vente, 0 pour une sortie. `outcome` est le résultat en multiples du
    risque quand il est connu, `None` tant qu'il ne l'est pas — un appel sans
    issue reste dans le registre, c'est précisément ce que la collecte
    prospective apporte.
    """

    ts: float
    pseudo: str
    instrument: str
    side: int
    outcome: float | None = None
    source: str = "direct"
    note: str = ""

    def __post_init__(self) -> None:
        if self.side not in (-1, 0, 1):
            raise ValueError("side vaut −1, 0 ou +1")
        if self.source not in SOURCES:
            raise ValueError(f"source inconnue : {self.source!r}")


@dataclass
class Ledger:
    """Le registre d'un diffuseur, et l'audit qui décide de sa recevabilité."""

    pseudo: str
    calls: list[Call] = field(default_factory=list)

    def add(self, call: Call) -> None:
        if call.pseudo != self.pseudo:
            raise ValueError("le pseudo de l'appel ne correspond pas")
        self.calls.append(call)

    @property
    def directional(self) -> list[Call]:
        return [c for c in self.calls if c.side != 0]

    @property
    def resolved(self) -> list[Call]:
        return [c for c in self.directional if c.outcome is not None]

    @property
    def retrospective_share(self) -> float:
        """Part des appels connus par récapitulatif plutôt que par le direct."""
        d = self.directional
        if not d:
            return 0.0
        return sum(1 for c in d if c.source == "recapitulatif") / len(d)

    @property
    def hit_rate(self) -> float:
        r = self.resolved
        if not r:
            return 0.0
        return sum(1 for c in r if (c.outcome or 0.0) > 0.0) / len(r)

    @property
    def mean_outcome(self) -> float:
        r = self.resolved
        if not r:
            return 0.0
        return sum(c.outcome or 0.0 for c in r) / len(r)

    @property
    def sd_outcome(self) -> float:
        r = self.resolved
        if len(r) < 2:
            return 0.0
        m = self.mean_outcome
        var = sum((float(c.outcome or 0.0) - m) ** 2 for c in r) / (len(r) - 1)
        return math.sqrt(var)

    def audit(self) -> list[str]:
        """Ce qui disqualifie un registre, énuméré plutôt que corrigé.

        Aucun de ces défauts n'est réparable après coup : un horodatage non
        monotone ne se réordonne pas sans supposer ce qu'on cherche à établir.
        Le registre reste lisible, mais l'audit accompagne toute lecture.
        """
        defauts: list[str] = []
        ts = [c.ts for c in self.calls]
        if any(b < a for a, b in zip(ts, ts[1:])):
            defauts.append("horodatage non monotone : ordre d'arrivée perdu")
        vus: set[tuple[float, str, int]] = set()
        for c in self.calls:
            cle = (round(c.ts, 3), c.instrument, c.side)
            if cle in vus:
                defauts.append("appels dupliqués à l'horodatage près")
                break
            vus.add(cle)
        part = self.retrospective_share
        if part > 0.0:
            defauts.append(
                f"{part:.0%} des appels viennent d'un récapitulatif : "
                "la fraction effacée n'est pas observable")
        sans = len(self.directional) - len(self.resolved)
        if sans and self.resolved:
            defauts.append(f"{sans} appel(s) sans issue connue, exclus des taux")
        return defauts


# --- Le verdict sur un diffuseur --------------------------------------------

@dataclass(frozen=True)
class Verdict:
    """Ce que le dépôt peut affirmer d'un diffuseur, et ce qu'il ne peut pas."""

    pseudo: str
    n_calls: int
    hit_rate: float
    p_null: float
    lift: float
    calls_alone: float
    calls_in_crowd: float
    crowd_hit_rate: float
    deletion_explaining: float
    min_half_life_s: float
    defauts: list[str]

    @property
    def decidable(self) -> bool:
        """Vrai si l'échantillon suffit au classement dans lequel il est lu."""
        return self.lift > 0.0 and self.n_calls >= self.calls_in_crowd

    @property
    def above_crowd(self) -> bool:
        """Vrai si le taux affiché dépasse ce que le classement fabrique seul."""
        return self.hit_rate > self.crowd_hit_rate

    def reading(self) -> str:
        if self.lift <= 0.0:
            return ("aucun avantage affiché sur la loi nulle : il n'y a rien "
                    "à décider, et aucune collecte ne changera cela")
        if not self.decidable:
            manque = self.calls_in_crowd - self.n_calls
            return (f"non décidable : il manque {manque:,.0f} appels pour "
                    f"trancher au rang où ce diffuseur est lu")
        if not self.above_crowd:
            return ("décidable, et négatif : le taux affiché reste sous ce "
                    "que le classement d'une foule sans talent produit")
        return ("décidable, et positif au seuil retenu ; reste à opposer "
                "l'audit du registre et la frontière de latence")


def evaluate(ledger: Ledger, p_null: float = 0.5, n_broadcasters: int = 1,
             delay_s: float = LATENCY_BOX_S[1],
             drift_ratio: float = 2.0,
             alpha: float = 0.05, power: float = 0.80) -> Verdict:
    """Applique au registre les quatre bornes du module.

    `p_null` est la fréquence de l'issue sous prix sans dérive : un demi pour
    un appel directionnel jugé au signe, `1/(R+1)` pour une géométrie à
    barrières. `n_broadcasters` est le nombre de diffuseurs **regardés**, pas
    le nombre retenu — c'est la taille de la famille, et c'est elle qui fixe
    le seuil.
    """
    n = len(ledger.resolved)
    p = ledger.hit_rate
    lift = p - p_null
    # Un registre sans avantage affiché n'a rien à faire trancher : le seuil
    # d'échantillon est infini, et c'est la réponse juste plutôt qu'un très
    # grand nombre produit par un plancher arbitraire.
    return Verdict(
        pseudo=ledger.pseudo,
        n_calls=n,
        hit_rate=p,
        p_null=p_null,
        lift=lift,
        calls_alone=(calls_to_decide(p_null, p_null + lift, alpha=alpha,
                                     power=power)
                     if lift > 0.0 else math.inf),
        calls_in_crowd=(crowd_threshold_calls(n_broadcasters, lift,
                                              p_null=p_null, alpha=alpha,
                                              power=power)
                        if lift > 0.0 else math.inf),
        crowd_hit_rate=hit_rate_of_crowd(n_broadcasters, max(n, 1), p_null),
        deletion_explaining=(deletion_explaining(p_null, p)
                             if p > p_null else 0.0),
        min_half_life_s=min_half_life(delay_s, drift_ratio),
        defauts=ledger.audit(),
    )


# --- Le consensus : une attention datée, pas une prévision ------------------

def consensus(calls: list[Call], at: float, window_s: float = 300.0) -> float:
    """Déséquilibre directionnel de la foule sur une fenêtre glissante.

    Vaut ``(n_achats − n_ventes)/(n_achats + n_ventes)`` sur les appels reçus
    dans les `window_s` secondes précédant `at`, un diffuseur ne comptant
    qu'une fois — sans quoi le plus bavard décide, et le bavardage est
    précisément ce que Kakhbod et al. associent à l'absence de talent.

    Ce que la grandeur mesure est une **attention simultanée**. Le document
    range cette information du côté de la capacité et de la friction : une
    foule qui regarde le même niveau au même instant y déplace le carnet, elle
    n'y déplace pas l'espérance.
    """
    if window_s <= 0.0:
        raise ValueError("window_s doit être > 0")
    dernier: dict[str, int] = {}
    for c in calls:
        if c.side != 0 and at - window_s <= c.ts <= at:
            dernier[c.pseudo] = c.side
    if not dernier:
        return 0.0
    sens = list(dernier.values())
    return sum(sens) / len(sens)


def crowding_bits(imbalance: float, n_voices: int) -> float:
    """Information maximale qu'un déséquilibre de foule peut porter, en bits.

    Un déséquilibre observé sur `n` voix est une statistique binomiale ; ce
    qu'elle peut au mieux dire d'une issue binaire est borné par l'entropie de
    la fréquence observée écartée de sa valeur d'équilibre. La borne est
    optimiste — elle suppose que tout l'écart est informatif — et sert donc à
    **rejeter** : si la borne optimiste reste sous l'exigence de `entropy`,
    la couche est réfutée sans avoir à la mesurer.
    """
    if n_voices < 1:
        raise ValueError("n_voices doit être ≥ 1")
    from .entropy import kl_bernoulli
    p = min(max((1.0 + imbalance) / 2.0, 1e-12), 1.0 - 1e-12)
    return kl_bernoulli(p, 0.5) * (1.0 - 1.0 / (1.0 + n_voices))


# --- La capture, et pourquoi elle est manuelle ------------------------------

TAPE_HEADER = "ts,pseudo,instrument,side,outcome,source,note"

#: Aide-mémoire du mode d'enregistrement. Une frappe, un horodatage.
TAPE_HELP = """\
Enregistrement d'un direct — une ligne par appel, validée par Entrée.

  l [note]     appel à l'achat          s [note]     appel à la vente
  x [note]     sortie annoncée          r <±R>       issue du dernier appel
  ?            rappel de ces touches    q            fin de séance

L'horodatage est celui de la **réception**, pris à la validation de la ligne.
Il n'est pas celui de l'émetteur, et l'écart entre les deux est exactement la
latence que le module facture. Aucune donnée n'est prélevée sur la plateforme :
seule la frappe du spectateur entre dans le registre."""


def parse_tape_line(line: str, pseudo: str, instrument: str,
                    ts: float) -> Call | None:
    """Traduit une ligne d'enregistrement en appel. Rend `None` si sans objet."""
    txt = line.strip()
    if not txt:
        return None
    tete, _, reste = txt.partition(" ")
    sens = {"l": 1, "s": -1, "x": 0}.get(tete.lower())
    if sens is None:
        return None
    return Call(ts=ts, pseudo=pseudo, instrument=instrument, side=sens,
                source="direct", note=reste.strip())


def to_csv(ledger: Ledger) -> str:
    """Rend le registre au format que `from_csv` relit, en-tête comprise."""
    lignes = [TAPE_HEADER]
    for c in ledger.calls:
        issue = "" if c.outcome is None else f"{c.outcome:.6f}"
        note = c.note.replace(",", ";").replace("\n", " ")
        lignes.append(f"{c.ts:.3f},{c.pseudo},{c.instrument},{c.side},"
                      f"{issue},{c.source},{note}")
    return "\n".join(lignes) + "\n"


def from_csv(text: str) -> dict[str, Ledger]:
    """Relit un ou plusieurs registres. Une ligne mal formée arrête la lecture.

    Le refus est délibéré : une ligne ignorée en silence est une observation
    supprimée, et le module entier porte sur ce que la suppression d'une
    observation fait à une conclusion.
    """
    lignes = [l for l in text.splitlines() if l.strip()]
    if not lignes:
        return {}
    if lignes[0].replace(" ", "") != TAPE_HEADER:
        raise ValueError(f"en-tête attendue : {TAPE_HEADER}")
    registres: dict[str, Ledger] = {}
    for i, ligne in enumerate(lignes[1:], start=2):
        champs = ligne.split(",")
        if len(champs) < 6:
            raise ValueError(f"ligne {i} : six champs attendus")
        ts, pseudo, instrument, side, issue, source = champs[:6]
        note = champs[6] if len(champs) > 6 else ""
        call = Call(ts=float(ts), pseudo=pseudo, instrument=instrument,
                    side=int(side),
                    outcome=None if issue.strip() == "" else float(issue),
                    source=source.strip(), note=note)
        registres.setdefault(pseudo, Ledger(pseudo)).add(call)
    return registres


def record(pseudo: str, instrument: str, lines, clock=time.time) -> Ledger:
    """Construit un registre à partir d'un flux de lignes horodatées à l'arrivée.

    `lines` est n'importe quel itérable de chaînes — `sys.stdin` en usage
    réel, une liste en test. `clock` est injecté pour que le test soit
    déterministe. La fonction ne lit rien d'autre que ce qui lui est donné :
    il n'y a pas de collecte automatique dans ce dépôt, et ce n'est pas une
    limite technique mais le seul régime de collecte que l'audit accepte.
    """
    registre = Ledger(pseudo)
    for ligne in lines:
        txt = ligne.strip()
        if txt.lower() in ("q", "quit"):
            break
        if txt == "?":
            continue
        if txt.lower().startswith("r ") and registre.calls:
            dernier = registre.calls[-1]
            registre.calls[-1] = Call(
                ts=dernier.ts, pseudo=dernier.pseudo,
                instrument=dernier.instrument, side=dernier.side,
                outcome=float(txt[2:].strip().replace(",", ".")),
                source=dernier.source, note=dernier.note)
            continue
        appel = parse_tape_line(ligne, pseudo, instrument, clock())
        if appel is not None:
            registre.add(appel)
    return registre


def main(pseudo: str | None = None) -> None:
    """Affiche les bornes du module, ou évalue un registre déjà collecté."""
    from .report7 import main as report7_main
    report7_main(pseudo)


if __name__ == "__main__":
    main()
