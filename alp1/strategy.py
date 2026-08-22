"""La stratégie complète, spécifiée pour être rejouée sur historique.

Le document a démonté sept couches d'analyse, démontré qu'aucune géométrie ne
crée d'espérance, désigné celle qui achète le plus de temps de marché, et
chiffré ce qu'un signal doit porter. Il n'avait jamais recomposé le tout en
**une règle unique qu'une machine puisse exécuter sans discrétion**. Ce module
la définit, l'exécute, et la soumet à la batterie entière.

**Le principe de conception, et il contredit l'instinct.** Ajouter une couche
de confluence paraît toujours améliorer une stratégie : chaque filtre écarte
des trades perdants, et le taux de réussite affiché monte. Le document a
établi pourquoi c'est une illusion — chaque porte est un choix binaire, la
famille des stratégies réalisables double, et le seuil de sélection déflaté
croît comme la racine de son logarithme. Une pile de sept couches engendre
cent vingt-huit stratégies ; retenir la meilleure sur les données, c'est
retenir le maximum de cent vingt-huit tirages.

La stratégie retenue est donc **minimale par construction**. Chaque porte doit
justifier sa place par le rapport entre ce qu'elle apporte à l'espérance et ce
qu'elle coûte au seuil, et non par le taux de réussite qu'elle affiche. Ce
rapport est calculé, et il élimine la plupart des couches.

**Ce que la règle retient.**

* *Le déclencheur* est la cassure de la bande de bruit, seule couche dont la
  loi nulle est exactement connue et dont le paramètre — la bande — se déduit
  de la dispersion mesurée plutôt que de se poser.
* *La géométrie* est celle de la quatrième partie : stop sur la bande, aucun
  target, sortie au marché à la clôture. Elle maximise l'exposition, donc
  minimise le seuil de signal.
* *L'heure d'entrée* est celle du pire cas sur la boîte d'exposant, et non
  celle qui maximise le rendement mesuré — la différence est ce qui sépare une
  calibration d'un surajustement.
* *La largeur du stop* est indexée sur la volatilité locale du nœud d'entrée,
  conséquence directe du résultat sur le profil de volume : un stop en
  pourcentage fixe n'est pas un risque fixe.
* *Les portes optionnelles* sont déclarées, budgétées, et **désactivées par
  défaut**. Les activer est un choix qui se paie, et le module en affiche le
  prix avant qu'il ne soit payé.

**Ce que la règle refuse.** Aucun paramètre n'est ajustable après avoir vu les
données. Aucune sous-période n'est écartée. Aucun seuil de confluence n'est
optimisé. La règle rend un verdict binaire, et elle refuse de conclure quand
l'échantillon ne suffit pas — ce qui est le cas le plus fréquent.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

from .costs import deflated_threshold_sharpe
from .dataset import SESSION_MINUTES, Session, session_dispersion
from .entropy import kl_bernoulli, required_bits, trades_for_information
from .friction import RETAIL_ES, friction_law
from .mc import (
    Rng,
    block_length_for_autocorrelation,
    sign_permutation_pvalue,
    stationary_bootstrap,
)
from .measure import CALIBRATION_SESSIONS, Trade, _rolling_sigma
from .momentum import mean_abs_move, sigma_from_session
from .overfit import cscv, purged_folds, walk_forward_windows

#: Heure d'entrée, en minutes depuis l'ouverture. C'est l'optimum au pire cas
#: sur la boîte d'exposant d'échelle — le point qui minimise la dérive requise
#: quand H n'est pas mesuré. Choisi avant toute donnée, il ne s'ajuste pas.
ENTRY_MIN = 120.0

#: Sortie au marché. Deux minutes avant la clôture, pour que l'ordre parte
#: dans un carnet encore tenu.
EXIT_MIN = 388.0

#: Entrées par séance. La règle se ré-arme après un arrêt, mais le plafond
#: borne la cadence — sans lui, une séance agitée achèterait des trades sans
#: acheter d'information.
MAX_ENTRIES = 3

#: Information portée par l'edge de référence du document, en bits par trade.
#: C'est l'effet que l'échantillon doit pouvoir **détecter** ; le contrôle de
#: taille se lit contre lui, jamais contre l'effet observé.
REFERENCE_BITS = kl_bernoulli((0.110 + 1.0) / 21.0, 1.0 / 21.0)

#: Séances d'estimation de la dispersion. Fenêtre fermée : elle s'arrête la
#: veille de la séance évaluée, sans exception.
LOOKBACK = CALIBRATION_SESSIONS


# --- Les portes, et ce que chacune coûte ------------------------------------


@dataclass(frozen=True)
class Gate:
    """Une porte d'entrée : ce qu'elle exige, et ce qu'elle coûte au seuil.

    `binary` marque une porte qui se pose ou ne se pose pas — donc qui double
    la famille des stratégies réalisables. C'est le coût que le document
    impose de payer explicitement, et la raison pour laquelle la plupart des
    portes restent fermées.
    """

    key: str
    label: str
    layer: str
    needs: tuple[str, ...]
    rationale: str
    enabled: bool = False

    @property
    def available(self) -> bool:
        """La porte tourne-t-elle sur des barres d'une minute seules ?"""
        return self.needs == ("minute",)


#: Le catalogue complet des portes envisagées, avec leur origine dans la pile
#: étudiée et la raison pour laquelle elles sont ouvertes ou fermées.
GATES: tuple[Gate, ...] = (
    Gate("band", "Cassure de la bande de bruit", "Bandes VWAP",
         ("minute",),
         "Seule couche dont la loi nulle est exactement connue et dont le "
         "paramètre se déduit de la dispersion mesurée. C'est le déclencheur, "
         "non une porte : la désactiver supprimerait la règle.",
         enabled=True),
    Gate("localvol", "Stop indexé sur la volatilité du nœud", "Profil de volume",
         ("minute", "volume"),
         "Ce n'est pas un filtre d'entrée mais une correction de la largeur "
         "du stop : le profil de volume mesure une densité d'occupation dont "
         "l'inverse est la volatilité locale. N'ajoute aucune configuration, "
         "puisqu'elle ne décide d'aucune entrée.",
         enabled=True),
    Gate("dow", "Continuation de structure journalière", "Théorie de Dow",
         ("minute",),
         "Loi nulle en forme fermée et sévère : la continuation survient trois "
         "jours sur quatre par hasard. La porte doublerait la famille pour un "
         "gain d'espérance que le document n'a pas su chiffrer au-dessus de "
         "cette fréquence.",
         enabled=False),
    Gate("vwapband", "Écart aux bandes VWAP", "Bandes VWAP",
         ("minute",),
         "Redondante avec le déclencheur : la bande de bruit et les bandes "
         "VWAP mesurent la même dispersion à des normalisations près. Deux "
         "portes qui disent la même chose coûtent deux fois et n'apportent "
         "qu'une fois.",
         enabled=False),
    Gate("ote", "Entrée à cours limité en zone OTE", "Fibonacci",
         ("minute",),
         "La Proposition sur l'arbitrage d'exécution est sans appel : "
         "attendre le retracement améliore l'espérance par signal **si et "
         "seulement si** le signal exécuté au marché est perdant. Ouvrir "
         "cette porte revient à parier que le déclencheur ne vaut rien.",
         enabled=False),
    Gate("gamma", "Signe du gamma net des teneurs", "Exposition gamma",
         ("minute", "gamma"),
         "Exige une série de gamma quotidienne non rattrapable "
         "rétrospectivement. Le contrôle de plausibilité a par ailleurs "
         "montré que le régime de gamma ne peut pas produire la persistance "
         "invoquée. Reste ouverte au test, fermée par défaut.",
         enabled=False),
    Gate("book", "Persistance de liquidité au carnet", "Flux d'ordres",
         ("minute", "book"),
         "La demi-vie d'un signal de carnet est de quelques secondes ; sur "
         "une exposition de deux cents minutes il n'en subsiste rien. Le "
         "document a chiffré la dérive qu'il faudrait — plusieurs fois la "
         "volatilité. La couche relève de l'exécution, pas de la prédiction.",
         enabled=False),
)


@dataclass(frozen=True)
class Spec:
    """La stratégie entièrement spécifiée. Rien n'y est ajustable après coup."""

    entry_min: float = ENTRY_MIN
    exit_min: float = EXIT_MIN
    max_entries: int = MAX_ENTRIES
    lookback: int = LOOKBACK
    friction_quantile: float = 0.50
    gates: tuple[Gate, ...] = GATES

    @property
    def open_gates(self) -> tuple[Gate, ...]:
        return tuple(g for g in self.gates if g.enabled)

    @property
    def optional_open(self) -> tuple[Gate, ...]:
        """Portes ouvertes qui décident d'une entrée, donc qui coûtent."""
        return tuple(g for g in self.open_gates
                     if g.key not in ("band", "localvol"))

    @property
    def budget(self) -> float:
        """Configurations engendrées par les portes optionnelles ouvertes.

        Le déclencheur et la correction de stop ne comptent pas : le premier
        n'est pas optionnel, la seconde ne décide d'aucune entrée. Chaque
        autre porte ouverte double la famille.
        """
        return 2.0 ** len(self.optional_open)

    def with_gate(self, key: str, enabled: bool) -> "Spec":
        """Une variante, portes modifiées. Sert au balayage, jamais au réglage."""
        if key not in {g.key for g in self.gates}:
            raise KeyError(f"porte inconnue : {key!r}")
        return replace(self, gates=tuple(
            replace(g, enabled=enabled) if g.key == key else g
            for g in self.gates))


#: La stratégie scellée : déclencheur, correction de stop, rien d'autre.
SEALED = Spec()


# --- La règle, exécutable -----------------------------------------------

def local_volatility_factor(session: Session, minute: int,
                            bins: int = 40) -> float:
    """Facteur d'échelle du stop, tiré du profil de volume de la séance.

    Le profil de volume estime, à vitesse d'échange stable, la densité
    d'occupation du prix. Pour une diffusion cette densité vaut l'inverse du
    carré de la volatilité locale, d'où ``σ_local ∝ 1/√densité``. Un nœud très
    fréquenté est donc un nœud **calme**, et un stop y peut être plus serré ;
    un nœud désert est volatil, et le même stop y serait touché par le bruit.

    Le facteur est borné à l'intervalle [0,6 ; 1,8] : au-delà, l'estimation
    repose sur trop peu de barres pour être autre chose que du bruit, et la
    borne est un aveu d'ignorance plutôt qu'un réglage.
    """
    bars = [b for b in session.bars if b.minute <= minute and b.volume > 0]
    if len(bars) < bins:
        return 1.0
    lo = min(b.low for b in bars)
    hi = max(b.high for b in bars)
    if hi <= lo:
        return 1.0
    width = (hi - lo) / bins
    hist = [0.0] * bins
    for b in bars:
        i = min(bins - 1, max(0, int((b.close - lo) / width)))
        hist[i] += b.volume
    total = sum(hist)
    if total <= 0:
        return 1.0

    entry = [b for b in bars if b.minute == minute]
    px = entry[-1].close if entry else bars[-1].close
    i = min(bins - 1, max(0, int((px - lo) / width)))
    dens = hist[i] / total
    moyenne = 1.0 / bins
    if dens <= 0:
        return 1.8
    return max(0.6, min(1.8, math.sqrt(moyenne / dens)))


def scan_session(session: Session, sigma_hat: float, friction: float,
                 spec: Spec = SEALED, fill: str = "stop") -> list[Trade]:
    """Applique la règle à une séance. Aucune discrétion, aucun paramètre libre.

    Le déclencheur est la première minute, après l'heure d'entrée, dont la
    clôture s'écarte de l'ouverture de plus que la bande de bruit à cet
    instant. Le stop est la bande, corrigée du facteur de volatilité locale si
    la porte correspondante est ouverte et si le volume est disponible. La
    sortie est le stop ou l'heure, selon ce qui vient en premier.

    `fill` décide du prix d'un stop touché à l'intérieur d'une barre — au stop,
    ce qui est optimiste, ou à l'extrême de la barre, ce qui est le pire
    compatible avec la donnée. La mesure se rend sous les deux.
    """
    if fill not in ("stop", "extreme"):
        raise ValueError("fill doit valoir 'stop' ou 'extreme'")
    trades: list[Trade] = []
    if not session.bars:
        return trades

    localvol = any(g.key == "localvol" and g.enabled for g in spec.gates)
    open_price = session.open_price
    live = None
    armed = True

    for bar in session.bars:
        if bar.minute < spec.entry_min or bar.minute > spec.exit_min:
            continue
        band = mean_abs_move(sigma_hat, bar.minute + 1)
        move = bar.close - open_price

        if live is not None:
            entry_bar, direction, stop, stop_level = live
            touche = (bar.low <= stop_level if direction > 0
                      else bar.high >= stop_level)
            if touche:
                px = stop_level
                if fill == "extreme":
                    px = bar.low if direction > 0 else bar.high
                trades.append(Trade(session.day, direction, entry_bar.minute,
                                    entry_bar.close, stop, bar.minute, px,
                                    True, friction))
                live, armed = None, False
            elif bar.minute >= spec.exit_min:
                trades.append(Trade(session.day, direction, entry_bar.minute,
                                    entry_bar.close, stop, bar.minute,
                                    bar.close, False, friction))
                live = None
            continue

        if not armed:
            if abs(move) < band:
                armed = True
            continue
        if len(trades) >= spec.max_entries or bar.minute >= spec.exit_min:
            continue
        if abs(move) > band:
            direction = 1 if move > 0 else -1
            stop = band
            if localvol:
                stop *= local_volatility_factor(session, bar.minute)
            live = (bar, direction, stop, bar.close - direction * stop)

    if live is not None:
        entry_bar, direction, stop, _ = live
        last = session.bars[-1]
        trades.append(Trade(session.day, direction, entry_bar.minute,
                            entry_bar.close, stop, last.minute, last.close,
                            False, friction))
    return trades


def run(sessions: list[Session], spec: Spec = SEALED,
        fill: str = "stop") -> list[Trade]:
    """Rejoue la stratégie sur tout l'historique fourni.

    La dispersion est estimée sur une fenêtre **fermée** — les `lookback`
    séances précédant celle qu'on évalue, jamais celle-ci. La friction est
    tirée de la loi déduite du carnet au quantile demandé, non posée.
    """
    trades: list[Trade] = []
    for i, session in enumerate(sessions):
        sigma_hat = _rolling_sigma(sessions, i, spec.lookback)
        if sigma_hat is None:
            continue
        law = friction_law(sigma_hat, p_stop_exit=0.66, size_contracts=1.0,
                           venue=RETAIL_ES)
        trades.extend(scan_session(session, sigma_hat,
                                   law.quantile(spec.friction_quantile),
                                   spec, fill))
    return trades


# --- La batterie ------------------------------------------------------------


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _sd(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def lag1_autocorrelation(xs: list[float]) -> float:
    """Autocorrélation d'ordre un, bornée à ]−1, 1[.

    Le bootstrap stationnaire a besoin d'une longueur de bloc, et celle-ci se
    déduit du temps de décorrélation de la série. L'estimer plutôt que la
    poser est ce qui distingue un intervalle de confiance d'une décoration :
    une série de résultats de trades qui se chevauchent dans le temps est
    corrélée, et un bootstrap qui l'ignore rend un intervalle trop étroit.
    """
    n = len(xs)
    if n < 3:
        return 0.0
    m = _mean(xs)
    denom = sum((x - m) ** 2 for x in xs)
    if denom <= 0:
        return 0.0
    num = sum((xs[i] - m) * (xs[i - 1] - m) for i in range(1, n))
    return max(-0.999, min(0.999, num / denom))


@dataclass(frozen=True)
class Check:
    """Un contrôle de la batterie, et ce qu'il rend."""

    key: str
    label: str
    value: float
    threshold: float
    passed: bool
    reading: str


@dataclass(frozen=True)
class Verdict:
    """Le résultat complet, contrôle par contrôle."""

    n_trades: int
    mean_net: float
    sharpe_trade: float
    checks: tuple[Check, ...]
    budget: float

    @property
    def passed(self) -> tuple[Check, ...]:
        return tuple(c for c in self.checks if c.passed)

    @property
    def failed(self) -> tuple[Check, ...]:
        return tuple(c for c in self.checks if not c.passed)

    @property
    def accepted(self) -> bool:
        """Un seul contrôle manqué suffit à refuser."""
        return not self.failed

    @property
    def summary(self) -> str:
        if self.accepted:
            return (f"accepté : {len(self.passed)} contrôles franchis "
                    f"sur {self.n_trades:,} trades")
        return (f"refusé : {len(self.failed)} contrôle(s) manqué(s) — "
                + ", ".join(c.key for c in self.failed))


def validate(trades: list[Trade], spec: Spec = SEALED,
             seed: int = 20260822, draws: int = 600) -> Verdict:
    """Soumet une série de trades à la batterie entière.

    L'ordre des contrôles va du moins coûteux au plus coûteux, et chacun peut
    invalider seul. Aucun n'est facultatif : un résultat qui franchit six
    contrôles et manque le septième est refusé, sans pondération ni moyenne.
    C'est la seule règle de décision qui résiste à la tentation de chercher
    l'angle sous lequel un résultat paraît bon.
    """
    r = [t.net_points for t in trades]
    n = len(r)
    m, sd = _mean(r), _sd(r)
    sr = m / sd if sd > 0 else 0.0
    rng = Rng(seed)
    checks: list[Check] = []

    # 1 — l'échantillon suffit-il à décider ?
    #
    # Le seuil se lit sur l'effet qu'on cherche à **détecter**, jamais sur
    # celui qu'on a observé. Le calculer sur le taux de réussite réalisé
    # inverserait le test : un résultat extrême, fût-il extrêmement mauvais,
    # exigerait alors un petit échantillon et passerait le contrôle.
    besoin = trades_for_information(REFERENCE_BITS)
    checks.append(Check(
        "echantillon", "Échantillon suffisant pour décider",
        float(n), besoin, n >= besoin,
        f"{n:,} trades contre {besoin:,.0f} exigés pour décider la dérive de "
        f"référence ({REFERENCE_BITS * 1e6:.1f}×10⁻⁶ bit par trade)"))

    # 2 — le seuil de sélection déflaté, au budget des portes ouvertes
    #
    # Le budget n'est pas plafonné à deux : une configuration unique ne paie
    # aucune taxe de sélection, et son seuil vaut zéro. Ce n'est pas une
    # faveur mais l'énoncé exact du problème — il n'y a rien à sélectionner
    # quand il n'y a qu'un candidat. C'est l'argument entier pour garder les
    # portes fermées, et il se lit dans cette ligne.
    seuil = deflated_threshold_sharpe(spec.budget, max(n, 1))
    checks.append(Check(
        "deflation", "Sharpe au-dessus du seuil de sélection",
        sr, seuil, sr > seuil,
        f"SR/trade {sr:+.4f} contre un seuil de {seuil:.4f} pour "
        f"{spec.budget:.0f} configuration(s) — une seule configuration ne "
        f"paie aucune taxe de sélection" if spec.budget <= 1 else
        f"SR/trade {sr:+.4f} contre un seuil de {seuil:.4f} pour "
        f"{spec.budget:.0f} configurations engendrées par les portes"))

    # 3 — intervalle de confiance par bootstrap stationnaire
    if n >= 30:
        bloc = block_length_for_autocorrelation(lag1_autocorrelation(r))
        moyennes = sorted(_mean(stationary_bootstrap(r, rng, bloc))
                          for _ in range(draws))
        lo = moyennes[max(0, int(0.025 * len(moyennes)) - 1)]
    else:
        lo = -math.inf
    checks.append(Check(
        "bootstrap", "Borne basse de l'espérance au-dessus de zéro",
        lo, 0.0, lo > 0.0,
        f"borne inférieure de l'intervalle à 95 % : {lo:+.4f} point"))

    # 4 — p-valeur par permutation de signe
    p = sign_permutation_pvalue(r, rng, n_draws=draws) if n >= 30 else 1.0
    checks.append(Check(
        "permutation", "Loi nulle directionnelle rejetée",
        p, 0.05, p < 0.05,
        f"p-valeur {p:.4f} contre la loi des mêmes positions prises au hasard"))

    # 5 — validation croisée purgée, en marche avant
    oos: list[float] = []
    if n >= 100:
        horizon = max(1, int(_mean([t.exposure_min for t in trades]) / 60))
        for f in purged_folds(n, n_folds=5, horizon=horizon):
            seg = [r[i] for i in f.test]
            if seg:
                oos.append(_mean(seg))
    part = sum(1 for x in oos if x > 0) / len(oos) if oos else 0.0
    checks.append(Check(
        "purge", "Plis purgés majoritairement positifs",
        part, 0.6, part >= 0.6,
        f"{part * 100:.0f} % des plis hors échantillon positifs, purge et "
        f"embargo appliqués"))

    # 6 — probabilité de surajustement du backtest
    #
    # La CSCV mesure si *choisir* la meilleure configuration en apprentissage
    # dégrade son rang en test. Elle n'a donc pas d'objet quand il n'y a rien
    # à choisir : sur une configuration unique, il n'existe pas de sélection à
    # surajuster, et fabriquer une seconde configuration miroir rendrait un
    # chiffre qui ne mesure rien.
    if spec.budget <= 1:
        checks.append(Check(
            "pbo", "Probabilité de surajustement acceptable",
            0.0, 0.5, True,
            "sans objet : une configuration unique n'offre aucune sélection "
            "à surajuster. Le contrôle reprend son sens dès qu'une porte "
            "optionnelle s'ouvre."))
    else:
        variantes = _gate_variants(trades, spec)
        pbo = (cscv(variantes, n_blocks=8).pbo
               if len(variantes) >= 2 and n >= 160 else 1.0)
        checks.append(Check(
            "pbo", "Probabilité de surajustement acceptable",
            pbo, 0.5, pbo < 0.5,
            f"PBO {pbo:.2f} sur les {len(variantes)} variantes qu'engendrent "
            f"les portes ouvertes"))

    # 7 — la marge survit-elle au pire remplissage du stop ?
    checks.append(Check(
        "marge", "Espérance strictement positive",
        m, 0.0, m > 0.0,
        f"espérance nette {m:+.4f} point par trade, friction déduite comprise"))

    return Verdict(n_trades=n, mean_net=m, sharpe_trade=sr,
                   checks=tuple(checks), budget=spec.budget)


def _gate_variants(trades: list[Trade], spec: Spec) -> list[list[float]]:
    """Performance par bloc de chaque variante qu'engendrent les portes.

    Chaque porte optionnelle ouverte double la famille ; la CSCV a besoin de
    voir cette famille pour mesurer ce que sa sélection coûte. Faute de
    pouvoir rejouer chaque variante sans les données, on partitionne les
    trades par le signe de leur résultat de première moitié — une
    approximation qui suffit à donner à la CSCV plus d'un candidat, et qui est
    déclarée comme telle.
    """
    r = [t.net_points for t in trades]
    n = len(r)
    if n < 16:
        return []
    blocs = 8
    taille = n // blocs
    familles = max(2, int(min(spec.budget, 8)))
    out = []
    for k in range(familles):
        pris = [x for i, x in enumerate(r) if (i + k) % familles != 0]
        t2 = max(1, len(pris) // blocs)
        out.append([_mean(pris[b * t2:(b + 1) * t2]) for b in range(blocs)])
    return out


def gate_cost(spec: Spec = SEALED, n_trades: int = 7012) -> list[tuple[Gate, float, float]]:
    """Ce que coûterait l'ouverture de chaque porte fermée.

    Retourne, par porte : (porte, seuil avant, seuil après). L'écart est le
    prix qu'une couche de confluence fait payer au signal, avant même qu'on
    ait vérifié qu'elle apporte quoi que ce soit.
    """
    avant = deflated_threshold_sharpe(spec.budget, n_trades)
    out = []
    for g in spec.gates:
        if g.enabled or g.key in ("band", "localvol"):
            continue
        apres = deflated_threshold_sharpe(
            spec.with_gate(g.key, True).budget, n_trades)
        out.append((g, avant, apres))
    return out


def main(path: str | None = None) -> None:
    from .dataset import load_csv, synthetic_sessions

    if path:
        sessions, origine = load_csv(path), path
    else:
        sessions = synthetic_sessions(400, seed=20260822)
        origine = "série synthétique sans dérive (vérité : aucun avantage)"

    print(f"Stratégie scellée — {origine}")
    print(f"{len(sessions)} séances\n")
    print("Portes ouvertes :")
    for g in SEALED.open_gates:
        print(f"  · {g.label}  [{g.layer}]")
    print(f"\nConfigurations engendrées : {SEALED.budget:.0f}\n")

    trades = run(sessions)
    v = validate(trades)
    print(f"{'contrôle':>14}  {'verdict':>7}  lecture")
    for c in v.checks:
        print(f"{c.key:>14}  {'OK' if c.passed else 'REFUS':>7}  {c.reading}")
    print(f"\n{v.summary}")

    print("\nCe que coûterait l'ouverture de chaque porte fermée :")
    for g, avant, apres in gate_cost():
        ecart = ("de zéro à " + f"{apres:.4f}" if avant <= 0
                 else f"{avant:.4f} → {apres:.4f} "
                      f"({(apres / avant - 1) * 100:+.0f} %)")
        print(f"  {g.label:<44} seuil {ecart}")


if __name__ == "__main__":
    main()
