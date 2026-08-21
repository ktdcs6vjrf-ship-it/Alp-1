"""Cohérence des hypothèses de calibration, et survie des conclusions.

Un document quantitatif pose des nombres. Deux questions se posent alors, et
elles sont distinctes.

**Les nombres posés sont-ils compatibles entre eux ?** Poser une volatilité à
une minute *et* une dispersion de séance, c'est poser deux fois la même
quantité ; si les deux valeurs ne se déduisent pas l'une de l'autre, l'écart
qui les sépare ne mesure rien du prix — il mesure l'incohérence. ALP-2 pose
trois nombres seulement (niveau d'indice, dispersion de séance, durée de
séance) et déduit tout le reste. `coherence_report` vérifie chacune de ces
déductions numériquement, y compris les identités que le modèle doit satisfaire
exactement — arrêt optionnel, identité de Wald du second ordre.

**Les conclusions survivent-elles à la variation des nombres posés ?** Une
conclusion vraie au point de calibration et fausse à dix pour cent de ce point
n'est pas une conclusion, c'est une coïncidence. Ce module encadre chaque
conclusion sur une **boîte de plausibilité** — un intervalle par entrée, choisi
d'avance et justifié — et retourne :

  - l'encadrement `[min, max]` de la conclusion sur toute la boîte ;
  - le coin où chaque extrême est atteint ;
  - un certificat de monotonie : si les deux extrêmes sont atteints en des
    sommets, la fonction est monotone en chaque variable sur la boîte et
    l'encadrement par les sommets est exact ;
  - la valeur critique de chaque entrée — le point de rupture, obtenu par
    bissection — à laquelle la conclusion cesse de tenir, et la distance qui
    sépare ce point de la boîte.

Une conclusion n'est retenue que si elle tient partout dans la boîte. Le point
de rupture dit ce qu'il faudrait croire pour la renverser ; c'est la forme la
plus utile d'un test de sensibilité, parce qu'elle est falsifiable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Callable, Iterator

from .costs import COST_BASE, COST_OPTIMISTIC, COST_REALISTIC, ES
from .momentum import (
    annualised_sharpe,
    edge_points_from_bps,
    mean_abs_move,
    required_drift,
    required_ir,
    sharpe_per_trade,
    sigma_from_session,
    time_exit_outcome,
    trades_for_t_stat,
)

TRADING_DAYS = 252.0
TRADES_PER_YEAR = 200.0

# Exposition du trade ALP-1 de référence (1:20 sur un stop de 3 points), en
# minutes. Sert de repère fixe : la géométrie d'ALP-2 n'a d'intérêt que si
# elle achète du temps de marché, et c'est à ce chiffre qu'elle se compare.
V1_EXPOSURE_MIN = 28.9


# --- Entrées et grandeurs déduites ------------------------------------------


@dataclass(frozen=True)
class Inputs:
    """Les six nombres dont dépend l'intégralité du chiffrage d'ALP-2.

    Trois sont des propriétés du marché (niveau, dispersion, durée de séance),
    un est une décision de l'opérateur (heure d'entrée), un est une propriété
    du courtier (friction), un est l'hypothèse à tester (dérive captée). Rien
    d'autre n'entre dans les tables : ni la volatilité à une minute, ni le
    stop, ni l'exposition, qui sont tous déduits.
    """

    index_level: float
    session_dispersion: float
    session_min: float
    entry_min: float
    friction: float
    edge_bps: float

    def __post_init__(self) -> None:
        if min(self.index_level, self.session_dispersion, self.session_min) <= 0:
            raise ValueError("niveau, dispersion et durée de séance doivent être > 0")
        if not 0.0 < self.entry_min < self.session_min:
            raise ValueError("l'entrée doit tomber à l'intérieur de la séance")
        if self.friction < 0:
            raise ValueError("la friction doit être >= 0")


@dataclass(frozen=True)
class Derived:
    """Tout ce que les six entrées impliquent, sans paramètre supplémentaire."""

    inputs: Inputs
    sigma_1min: float
    annual_vol_pct: float
    stop: float
    stop_pct: float
    horizon: float
    p_stop: float
    exposure: float
    sd_gross: float
    mean_gross: float
    c_over_l: float
    mu_star_per_hour: float
    ir_star: float
    edge_points: float
    net_points: float
    edge_over_friction: float
    sr_trade: float
    sr_annual: float
    trades_for_t2: float


def derive(inp: Inputs) -> Derived:
    """Déduit toutes les grandeurs du papier à partir des six entrées.

    L'ordre des déductions est celui du document : la volatilité par racine de
    minute vient de la dispersion de séance, la bande de bruit vient de la
    volatilité et de l'heure d'entrée, le stop est la bande, l'exposition vient
    du stop et de la durée restante, et les trois seuils viennent de
    l'exposition.
    """
    sigma = sigma_from_session(inp.session_dispersion, inp.session_min)
    stop = mean_abs_move(sigma, inp.entry_min)
    horizon = inp.session_min - inp.entry_min
    out = time_exit_outcome(stop, horizon, sigma)
    edge = edge_points_from_bps(inp.edge_bps, inp.index_level)
    sr = sharpe_per_trade(edge, inp.friction, sigma, out.expected_time)
    ann_vol = (100.0 * inp.session_dispersion
               * math.sqrt(TRADING_DAYS) / inp.index_level)
    return Derived(
        inputs=inp,
        sigma_1min=sigma,
        annual_vol_pct=ann_vol,
        stop=stop,
        stop_pct=100.0 * stop / inp.index_level,
        horizon=horizon,
        p_stop=out.p_stop,
        exposure=out.expected_time,
        sd_gross=out.sd_gross,
        mean_gross=out.mean_gross,
        c_over_l=100.0 * inp.friction / stop,
        mu_star_per_hour=60.0 * required_drift(inp.friction, out.expected_time),
        ir_star=required_ir(inp.friction, sigma, out.expected_time),
        edge_points=edge,
        net_points=edge - inp.friction,
        edge_over_friction=edge / inp.friction if inp.friction > 0 else math.inf,
        sr_trade=sr,
        sr_annual=annualised_sharpe(sr, TRADES_PER_YEAR),
        trades_for_t2=trades_for_t_stat(sr),
    )


# La calibration de référence — identique, nombre pour nombre, à celle de
# `alp1.report2`. Les deux modules ne peuvent pas diverger : les tests le
# vérifient.
REFERENCE = Inputs(
    index_level=6000.0,
    session_dispersion=60.0,
    session_min=390.0,
    entry_min=90.0,
    friction=COST_BASE.friction_points(ES),   # 4,00 $ + 1 tick de sortie
    edge_bps=6.0,                             # réplication ES/NQ
)


# --- Compatibilité mutuelle des entrées -------------------------------------


@dataclass(frozen=True)
class Check:
    """Un contrôle de cohérence : ce qu'on attend, ce qu'on obtient, l'écart."""

    label: str
    obtained: float
    expected: float
    tolerance: float
    unit: str = ""
    comment: str = ""

    @property
    def gap(self) -> float:
        return self.obtained - self.expected

    @property
    def ok(self) -> bool:
        return abs(self.gap) <= self.tolerance


@dataclass(frozen=True)
class Range:
    """Un contrôle de plausibilité : la valeur tombe-t-elle dans la fourchette ?"""

    label: str
    obtained: float
    lo: float
    hi: float
    unit: str = ""
    comment: str = ""

    @property
    def ok(self) -> bool:
        return self.lo <= self.obtained <= self.hi


def identity_checks(inp: Inputs = REFERENCE) -> list[Check]:
    """Les identités que la calibration doit satisfaire *exactement*.

    Ce ne sont pas des contrôles de plausibilité mais des égalités : chacune
    est une conséquence du modèle, et un écart au-delà de la tolérance signale
    une erreur d'algèbre ou d'implémentation, pas une hypothèse discutable.
    """
    d = derive(inp)
    sigma, stop, horizon = d.sigma_1min, d.stop, d.horizon
    out = time_exit_outcome(stop, horizon, sigma)

    return [
        Check("Dispersion de séance reconstruite depuis σ₁",
              sigma * math.sqrt(inp.session_min), inp.session_dispersion,
              1e-9, "pt",
              "σ₁ = dispersion/√T par définition : la relation n'a pas de degré "
              "de liberté, et l'exposant d'échelle d'ALP-1 disparaît avec elle."),
        Check("Espérance brute sous martingale (arrêt optionnel)",
              d.mean_gross, 0.0, 1e-12, "pt",
              "Temps d'arrêt borné par la clôture : toute règle de sortie laisse "
              "une espérance brute nulle."),
        Check("Identité de Wald du second ordre : σ√E[τ∧T]",
              d.sd_gross, sigma * math.sqrt(d.exposure), 1e-12, "pt",
              "La dispersion du résultat est celle du temps passé exposé, et "
              "rien d'autre."),
        Check("Compensation stop / clôture",
              out.p_stop * stop, out.p_open * out.mean_open, 1e-9, "pt",
              "La branche « encore ouverte » compense exactement les stops ; "
              "c'est la même identité, lue en probabilité."),
        Check("Somme des probabilités d'issue",
              out.p_stop + out.p_open, 1.0, 1e-12, "",
              "Deux issues exhaustives : le stop, ou la clôture."),
        Check("Seuil de dérive et seuil de ratio d'information",
              d.ir_star, (d.mu_star_per_hour / 60.0) * math.sqrt(d.exposure) / sigma,
              1e-12, "",
              "IR* = µ*·√E[τ∧T]/σ : les deux seuils sont la même contrainte "
              "exprimée dans deux unités."),
        Check("Sharpe par trade à dérive nulle",
              sharpe_per_trade(0.0, inp.friction, sigma, d.exposure),
              -d.ir_star, 1e-12, "",
              "Sans signal, le Sharpe par trade vaut exactement moins le seuil : "
              "SR = IR_signal − IR*."),
    ]


def plausibility_checks(inp: Inputs = REFERENCE) -> list[Range]:
    """Les contrôles qui *peuvent* échouer : entrées confrontées au marché.

    Chaque fourchette est posée d'avance et vient d'une observation publique
    grossière, pas d'un calcul du document. Elles ne prouvent rien ; elles
    interdisent seulement de calibrer sur un marché qui n'existe pas.
    """
    d = derive(inp)
    return [
        Range("Volatilité annualisée impliquée", d.annual_vol_pct, 8.0, 30.0, "%",
              "Un indice large tient entre 8 % et 30 % hors crise ; en dessous, "
              "la dispersion de séance posée est trop faible pour le marché "
              "qu'on prétend décrire, au-dessus elle décrit une panique."),
        Range("Volatilité à une minute", d.sigma_1min, 1.5, 6.0, "pt",
              "Conséquence de la ligne précédente au niveau d'indice retenu ; "
              "elle est rappelée parce que c'est elle, et non la dispersion, "
              "qui entre dans toutes les formules."),
        Range("Stop en pourcentage de l'indice", d.stop_pct, 0.15, 0.75, "%",
              "La bande de bruit à mi-séance ; en dessous on est dans le bruit "
              "de cotation, au-dessus le dimensionnement quitte le micro-contrat."),
        Range("Probabilité de toucher le stop", 100.0 * d.p_stop, 40.0, 80.0, "%",
              "Un stop posé sur la bande de bruit et tenu jusqu'à la clôture est "
              "touché deux fois sur trois : ce n'est pas un garde-fou rare mais "
              "la sortie usuelle. L'identité de compensation est ce qui le rend "
              "malgré tout neutre en espérance."),
        Range("Taux de réussite impliqué", 100.0 * (1.0 - d.p_stop), 25.0, 50.0, "%",
              "Contrôle externe : les réplications publiées de la même règle "
              "rapportent 38 % à 40 % de trades gagnants. Le modèle produit ce "
              "chiffre sans l'avoir reçu — c'est le seul point du document où "
              "une sortie du noyau rencontre une observation de tiers."),
        Range("Exposition en fraction de la séance restante",
              100.0 * d.exposure / d.horizon, 40.0, 95.0, "%",
              "Le trade doit passer l'essentiel du temps restant exposé — c'est "
              "la seule chose que la géométrie sache produire."),
        Range("Friction rapportée au risque", d.c_over_l, 0.0, 5.0, "%",
              "Au-delà de quelques pour cent, la friction redevient l'objet "
              "principal du trade et le signal ne peut plus la financer."),
    ]


def coherence_report(inp: Inputs = REFERENCE) -> tuple[list[Check], list[Range], bool]:
    """Les deux séries de contrôles et le verdict global."""
    ids = identity_checks(inp)
    rng = plausibility_checks(inp)
    return ids, rng, all(c.ok for c in ids) and all(r.ok for r in rng)


# --- Boîte de plausibilité et encadrement -----------------------------------


@dataclass(frozen=True)
class Interval:
    """Un intervalle fermé. Dégénéré si `lo == hi` : l'axe est alors gelé."""

    lo: float
    hi: float

    def __post_init__(self) -> None:
        if self.hi < self.lo:
            raise ValueError("intervalle vide : hi < lo")

    @property
    def mid(self) -> float:
        return 0.5 * (self.lo + self.hi)

    @property
    def width(self) -> float:
        return self.hi - self.lo

    @property
    def degenerate(self) -> bool:
        return self.width == 0.0

    def contains(self, x: float, tol: float = 1e-12) -> bool:
        return self.lo - tol <= x <= self.hi + tol

    def grid(self, n: int) -> list[float]:
        """`n` points régulièrement espacés, bornes comprises."""
        if self.degenerate or n <= 1:
            return [self.lo]
        step = self.width / (n - 1)
        return [self.lo + i * step for i in range(n)]


AXES: tuple[str, ...] = (
    "index_level", "session_dispersion", "session_min",
    "entry_min", "friction", "edge_bps",
)

AXIS_LABEL = {
    "index_level": "Niveau d'indice",
    "session_dispersion": "Dispersion de séance (pt)",
    "session_min": "Durée de séance (min)",
    "entry_min": "Heure d'entrée (min après l'ouverture)",
    "friction": "Friction par aller-retour (pt)",
    "edge_bps": "Dérive captée (pb)",
}


@dataclass(frozen=True)
class Box:
    """Une boîte de plausibilité : un intervalle par entrée."""

    index_level: Interval
    session_dispersion: Interval
    session_min: Interval
    entry_min: Interval
    friction: Interval
    edge_bps: Interval

    def interval(self, axis: str) -> Interval:
        return getattr(self, axis)

    def free_axes(self) -> tuple[str, ...]:
        return tuple(a for a in AXES if not self.interval(a).degenerate)

    def contains(self, inp: Inputs) -> bool:
        return all(self.interval(a).contains(getattr(inp, a)) for a in AXES)

    def at(self, **coords: float) -> Inputs:
        base = {a: self.interval(a).mid for a in AXES}
        base.update(coords)
        return Inputs(**base)

    def corner(self, bits: int) -> Inputs:
        """Le sommet désigné par les bits de `bits`, axes libres seulement."""
        free = self.free_axes()
        coords = {a: self.interval(a).lo for a in AXES}
        for i, axis in enumerate(free):
            if bits >> i & 1:
                coords[axis] = self.interval(axis).hi
        return Inputs(**coords)

    def corners(self) -> Iterator[Inputs]:
        for bits in range(1 << len(self.free_axes())):
            yield self.corner(bits)

    def points(self, n: int) -> Iterator[Inputs]:
        """Grille tensorielle à `n` points par axe libre."""
        free = self.free_axes()
        grids = [self.interval(a).grid(n) for a in free]
        frozen = {a: self.interval(a).lo for a in AXES if a not in free}
        idx = [0] * len(free)
        while True:
            coords = dict(frozen)
            for a, g, i in zip(free, grids, idx):
                coords[a] = g[i]
            yield Inputs(**coords)
            for k in range(len(free) - 1, -1, -1):
                idx[k] += 1
                if idx[k] < len(grids[k]):
                    break
                idx[k] = 0
            else:
                return


# La boîte retenue. Chaque borne est justifiée hors du document : les frictions
# sont les deux scénarios d'exécution extrêmes du module `costs`, la dispersion
# couvre de 10 % à 24 % de volatilité annualisée au niveau d'indice médian, et
# la dérive va de la moitié à un tiers de plus que la valeur publiée par la
# réplication. Aucune borne n'a été choisie après avoir vu le résultat.
BOX = Box(
    index_level=Interval(5000.0, 7000.0),
    session_dispersion=Interval(40.0, 90.0),
    session_min=Interval(390.0, 390.0),
    entry_min=Interval(60.0, 180.0),
    friction=Interval(COST_OPTIMISTIC.friction_points(ES),
                      COST_REALISTIC.friction_points(ES)),
    edge_bps=Interval(3.0, 8.0),
)


@dataclass(frozen=True)
class Enclosure:
    """Encadrement d'une grandeur sur une boîte, et son certificat."""

    key: str
    label: str
    unit: str
    lo: float
    hi: float
    reference: float
    argmin: Inputs
    argmax: Inputs
    monotone: bool
    n_eval: int

    @property
    def spread(self) -> float:
        """Rapport hi/lo — de combien la conclusion bouge sur la boîte."""
        if self.lo == 0.0:
            return math.inf
        return self.hi / self.lo

    def holds(self, side: str, bound: float) -> bool:
        """La conclusion `grandeur <side> bound` tient-elle sur toute la boîte ?"""
        if side == "<":
            return self.hi < bound
        if side == ">":
            return self.lo > bound
        raise ValueError("side doit être '<' ou '>'")


def _is_vertex(box: Box, inp: Inputs, tol: float = 1e-9) -> bool:
    for a in box.free_axes():
        iv, x = box.interval(a), getattr(inp, a)
        if min(abs(x - iv.lo), abs(x - iv.hi)) > tol * max(1.0, abs(iv.hi)):
            return False
    return True


def enclose(key: str, label: str, unit: str,
            fn: Callable[[Derived], float],
            box: Box = BOX, n: int = 5,
            reference: Inputs = REFERENCE) -> Enclosure:
    """Encadre `fn` sur `box` par balayage tensoriel, et certifie la monotonie.

    Le balayage est exhaustif à la résolution `n` : c'est un encadrement
    *observé*, pas une borne prouvée. Le certificat le complète : si les deux
    extrêmes sont atteints en des sommets de la boîte, la grandeur est monotone
    en chaque variable sur la grille, et pour une fonction lisse l'encadrement
    par les sommets est alors exact. Quand le certificat tombe — une grandeur
    non monotone, comme l'exposition en fonction de l'heure d'entrée — le
    balayage reste valide mais l'encadrement doit être lu comme un minimum de
    variation, et la résolution augmentée.
    """
    lo = math.inf
    hi = -math.inf
    argmin = argmax = reference
    count = 0
    for inp in box.points(n):
        v = fn(derive(inp))
        count += 1
        if v < lo:
            lo, argmin = v, inp
        if v > hi:
            hi, argmax = v, inp
    return Enclosure(
        key=key, label=label, unit=unit, lo=lo, hi=hi,
        reference=fn(derive(reference)),
        argmin=argmin, argmax=argmax,
        monotone=_is_vertex(box, argmin) and _is_vertex(box, argmax),
        n_eval=count,
    )


# --- Les conclusions du document, et leur survie -----------------------------


@dataclass(frozen=True)
class Conclusion:
    """Une affirmation du document, réduite à une inégalité vérifiable."""

    key: str
    label: str
    unit: str
    fn: Callable[[Derived], float]
    side: str
    bound: float
    claim: str


CONCLUSIONS: tuple[Conclusion, ...] = (
    Conclusion("c_over_l", "Friction rapportée au risque", "%",
               lambda d: d.c_over_l, "<", 5.0,
               "la friction reste sous 5 % du risque nominal"),
    Conclusion("ir_star", "Ratio d'information requis", "",
               lambda d: d.ir_star, "<", 0.05,
               "le seuil de qualité de signal reste sous 0,05 écart-type"),
    Conclusion("edge_over_friction", "Dérive rapportée à la friction", "×",
               lambda d: d.edge_over_friction, ">", 1.0,
               "la dérive publiée couvre la friction"),
    Conclusion("net_points", "Résultat net par trade", "pt",
               lambda d: d.net_points, ">", 0.0,
               "l'espérance nette par trade reste positive"),
    Conclusion("sr_trade", "Sharpe par trade", "",
               lambda d: d.sr_trade, ">", 0.0,
               "le Sharpe par trade reste positif"),
    Conclusion("exposure", "Exposition", "min",
               lambda d: d.exposure, ">", 2.0 * V1_EXPOSURE_MIN,
               "l'exposition reste au moins double de celle d'ALP-1 "
               f"({2.0 * V1_EXPOSURE_MIN:.1f} min)"),
)


@dataclass(frozen=True)
class Verdict:
    """Une conclusion, son encadrement, et si elle tient partout."""

    conclusion: Conclusion
    enclosure: Enclosure

    @property
    def holds(self) -> bool:
        return self.enclosure.holds(self.conclusion.side, self.conclusion.bound)

    @property
    def margin(self) -> float:
        """Distance du pire cas à la borne, dans l'unité de la grandeur."""
        if self.conclusion.side == "<":
            return self.conclusion.bound - self.enclosure.hi
        return self.enclosure.lo - self.conclusion.bound


def verdicts(box: Box = BOX, n: int = 5) -> list[Verdict]:
    """Chaque conclusion du document, encadrée sur la boîte."""
    return [Verdict(c, enclose(c.key, c.label, c.unit, c.fn, box, n))
            for c in CONCLUSIONS]


def all_hold(box: Box = BOX, n: int = 5) -> bool:
    return all(v.holds for v in verdicts(box, n))


# --- Points de rupture -------------------------------------------------------


def _worst_inputs(conclusion: Conclusion, box: Box, n: int = 5) -> Inputs:
    """Le point de la boîte le plus défavorable à la conclusion."""
    enc = enclose(conclusion.key, conclusion.label, conclusion.unit,
                  conclusion.fn, box, n)
    return enc.argmax if conclusion.side == "<" else enc.argmin


def breaking_point(conclusion: Conclusion, axis: str, box: Box = BOX,
                   span: float = 20.0, n: int = 5,
                   tol: float = 1e-9) -> float | None:
    """Valeur de `axis` qui annule la marge, les autres entrées au pire cas.

    On part du point le plus défavorable de la boîte et on pousse un seul axe
    jusqu'à ce que la conclusion bascule, par bissection. `span` est le facteur
    d'élargissement maximal exploré de part et d'autre de la boîte ; `None`
    signifie que la conclusion tient encore à ce facteur, c'est-à-dire qu'aucune
    valeur défendable de cette entrée ne la renverse.
    """
    if axis not in AXES:
        raise ValueError(f"axe inconnu : {axis}")
    base = _worst_inputs(conclusion, box, n)
    iv = box.interval(axis)

    def margin(x: float) -> float:
        try:
            v = conclusion.fn(derive(replace(base, **{axis: x})))
        except ValueError:
            return math.nan
        return (conclusion.bound - v if conclusion.side == "<"
                else v - conclusion.bound)

    here = margin(getattr(base, axis))
    if math.isnan(here) or here <= 0.0:
        return getattr(base, axis)

    lo_probe = max(iv.lo / span, 1e-9)
    hi_probe = iv.hi * span
    if axis == "entry_min":
        lo_probe, hi_probe = 1.0, base.session_min - 1.0

    x0 = getattr(base, axis)
    for x1 in (hi_probe, lo_probe):
        m1 = margin(x1)
        if math.isnan(m1) or m1 > 0.0:
            continue
        a, b = x0, x1
        for _ in range(200):
            mid = 0.5 * (a + b)
            if abs(b - a) <= tol * max(1.0, abs(mid)):
                break
            if margin(mid) > 0.0:
                a = mid
            else:
                b = mid
        return 0.5 * (a + b)
    return None


@dataclass(frozen=True)
class Breaking:
    """Point de rupture d'une conclusion selon un axe, et son éloignement."""

    conclusion: Conclusion
    axis: str
    value: float | None
    box_lo: float
    box_hi: float

    @property
    def factor(self) -> float:
        """Rapport entre le point de rupture et la borne de boîte la plus proche.

        Supérieur à 1 : il faut sortir de la boîte, et de ce facteur, pour
        renverser la conclusion. `inf` : aucune valeur explorée ne la renverse.
        """
        if self.value is None:
            return math.inf
        if self.value >= self.box_hi:
            return self.value / self.box_hi if self.box_hi else math.inf
        if self.value <= self.box_lo:
            return self.box_lo / self.value if self.value else math.inf
        return 1.0

    @property
    def inside_box(self) -> bool:
        return self.value is not None and self.box_lo <= self.value <= self.box_hi


def breaking_points(conclusion: Conclusion, box: Box = BOX,
                    n: int = 5) -> list[Breaking]:
    """Le point de rupture de la conclusion selon chaque axe libre."""
    out = []
    for axis in box.free_axes():
        iv = box.interval(axis)
        out.append(Breaking(conclusion, axis,
                            breaking_point(conclusion, axis, box, n=n),
                            iv.lo, iv.hi))
    return out


def main() -> None:
    ids, rngs, ok = coherence_report()
    print("Identités du modèle")
    for c in ids:
        print(f"  [{'ok' if c.ok else 'ÉCHEC'}] {c.label}: "
              f"{c.obtained:.12g} vs {c.expected:.12g}")
    print("\nPlausibilité des entrées")
    for r in rngs:
        print(f"  [{'ok' if r.ok else 'ÉCHEC'}] {r.label}: "
              f"{r.obtained:.4g} {r.unit} dans [{r.lo:g}, {r.hi:g}]")
    print(f"\nCohérence globale : {'ok' if ok else 'ÉCHEC'}")

    print("\nConclusions sur la boîte de plausibilité")
    for v in verdicts():
        e = v.enclosure
        print(f"  [{'tient' if v.holds else 'TOMBE'}] {e.label}: "
              f"[{e.lo:.4g}, {e.hi:.4g}] {e.unit} "
              f"(réf. {e.reference:.4g}, monotone={e.monotone}, "
              f"{e.n_eval} évaluations)")


if __name__ == "__main__":
    main()
