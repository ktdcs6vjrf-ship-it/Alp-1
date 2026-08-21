"""Exécution du protocole pré-enregistré sur un historique réel.

C'est le module qui manque au dépôt tant qu'aucun fichier de prix n'est
fourni, et le seul dont la sortie soit une mesure et non une déduction. Il ne
contient aucune décision libre : toutes les règles viennent de `alp1.prereg`,
gelées et scellées, et la friction vient de `alp1.friction`, déduite du carnet.
Le rôle de ce module est de les appliquer, pas de les choisir.

L'enchaînement est celui du protocole, et il s'interrompt de lui-même :

  1. **Calibration.** La dispersion de séance est mesurée sur l'historique, et
     `σ̂₁` en est déduite. Aucun des nombres du document n'est réutilisé — le
     fichier remplace la calibration, il ne la confirme pas.
  2. **Test 1 — fréquence.** À quelle fréquence la bande est-elle cassée ? Si
     c'est moins d'une séance sur deux, la règle ne se déclenche pas assez pour
     être testée et le protocole s'arrête là.
  3. **Test 2 — dérive captée.** Résultat net moyen par trade, Sharpe par
     trade, et confrontation au seuil de sélection à trois essais.
  4. **Test 3 — conditionnement gamma**, seulement si le test 2 est franchi.
  5. **Test 4 — heure d'entrée.** Une dérive concentrée sur une seule tranche
     est une signature de sélection, pas de structure.

Le résultat n'est pas un verdict de l'auteur : c'est `alp1.prereg.decide`
appliqué au chiffre mesuré, avec un seuil fixé avant que le fichier n'existe.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .dataset import SESSION_MINUTES, Session, session_dispersion
from .friction import RETAIL_ES, friction_law
from .momentum import mean_abs_move, sigma_from_session
from .power import SEALED_MAX_INFORMATION
from .prereg import PROTOCOL, Decision, Protocol, decide, spend
from .varratio import hurst_regression, null_grid, scan

WINDOW_OPEN = {"C1": 30, "C2": 30, "C3": 90}    # minutes après l'ouverture
EXIT_MINUTE = 388                                # 15:58 ET
MODEL_STOP_RATE = 0.66                           # P(stop) du noyau, cf. report2
CALIBRATION_SESSIONS = 14
MAX_ENTRIES = PROTOCOL.max_entries_per_session


@dataclass(frozen=True)
class Trade:
    """Un trade produit par la règle, du déclenchement à la sortie."""

    day: str
    direction: int
    entry_minute: int
    entry_price: float
    stop_distance: float
    exit_minute: int
    exit_price: float
    stopped: bool
    friction: float

    @property
    def gross_points(self) -> float:
        return self.direction * (self.exit_price - self.entry_price)

    @property
    def net_points(self) -> float:
        return self.gross_points - self.friction

    @property
    def exposure_min(self) -> float:
        return float(self.exit_minute - self.entry_minute)

    @property
    def net_r(self) -> float:
        return self.net_points / self.stop_distance if self.stop_distance else 0.0


def _rolling_sigma(sessions: list[Session], index: int,
                   window: int = CALIBRATION_SESSIONS) -> float | None:
    """`σ̂₁` estimée sur les `window` séances **précédant** celle d'indice donné.

    Fenêtre close et strictement antérieure : la séance mesurée n'entre jamais
    dans sa propre calibration. C'est la seule protection contre la fuite
    d'information qui compte ici, et elle est structurelle plutôt que déclarée.
    """
    if index < window:
        return None
    past = sessions[index - window:index]
    return sigma_from_session(session_dispersion(past), SESSION_MINUTES)


def scan_session(session: Session, sigma_hat: float, window_open: int,
                 friction: float, exit_minute: int = EXIT_MINUTE,
                 max_entries: int = MAX_ENTRIES,
                 fill: str = "stop") -> list[Trade]:
    """Applique la règle à une séance : jusqu'à trois trades, aucune discrétion.

    La cassure est la première minute, après l'ouverture de la fenêtre, dont la
    clôture s'écarte de l'ouverture de plus que la bande de bruit à cet
    instant. Le stop est la bande elle-même. La sortie est le stop ou l'heure,
    selon ce qui vient en premier.

    `fill` décide de la seule chose que des barres d'une minute ne tranchent
    pas : le prix auquel un stop touché **à l'intérieur** d'une barre est
    exécuté.

      ``"stop"``    au niveau du stop. Optimiste, et le reste : la loi de
                    friction porte le glissement séparément.
      ``"extreme"`` à l'extrême de la barre de franchissement — le bas pour un
                    achat, le haut pour une vente. C'est le pire remplissage
                    compatible avec la barre observée.

    Le vrai prix est entre les deux, et aucune donnée d'une minute ne dit où.
    Rejouer la mesure sous les deux règles encadre donc la conclusion sans
    rien supposer : si elle bascule entre les deux bornes, la mesure sur barres
    ne conclut pas, et il faut du tick. C'est la seule lecture honnête d'un
    stop de trois points touché deux fois sur trois.

    Après une sortie au stop, la règle se **ré-arme** : elle n'accepte une
    nouvelle cassure qu'une fois le prix revenu à l'intérieur de la bande.
    Sans cette condition, un stop serait immédiatement suivi d'une entrée au
    même endroit, et la cadence achèterait des trades sans acheter
    d'information. Le plafond de trois entrées est scellé, la règle de
    ré-armement aussi ; ni l'un ni l'autre n'est ajustable après coup.
    """
    if fill not in ("stop", "extreme"):
        raise ValueError("fill doit valoir 'stop' ou 'extreme'")
    trades: list[Trade] = []
    if not session.bars:
        return trades
    open_price = session.open_price
    live = None
    armed = True
    for bar in session.bars:
        if bar.minute < window_open or bar.minute > exit_minute:
            continue
        band = mean_abs_move(sigma_hat, bar.minute + 1)
        move = bar.close - open_price

        if live is not None:
            entry_bar, direction, stop, stop_level = live
            breached = (bar.low <= stop_level if direction > 0
                        else bar.high >= stop_level)
            if breached:
                exit_px = stop_level
                if fill == "extreme":
                    exit_px = bar.low if direction > 0 else bar.high
                trades.append(Trade(session.day, direction, entry_bar.minute,
                                    entry_bar.close, stop, bar.minute,
                                    exit_px, True, friction))
                live, armed = None, False
            elif bar.minute >= exit_minute:
                trades.append(Trade(session.day, direction, entry_bar.minute,
                                    entry_bar.close, stop, bar.minute,
                                    bar.close, False, friction))
                live = None
            continue

        if not armed:
            if abs(move) < band:
                armed = True
            continue
        if len(trades) >= max_entries or bar.minute >= exit_minute:
            continue
        if abs(move) > band:
            direction = 1 if move > 0 else -1
            live = (bar, direction, band, bar.close - direction * band)

    if live is not None:
        entry_bar, direction, stop, _ = live
        last = session.bars[-1]
        trades.append(Trade(session.day, direction, entry_bar.minute,
                            entry_bar.close, stop, last.minute, last.close,
                            False, friction))
    return trades


@dataclass(frozen=True)
class Measurement:
    """Le résultat d'une configuration sur un historique, et sa décision."""

    config_key: str
    n_sessions: int
    n_scanned: int
    trades: tuple[Trade, ...]
    sigma_hat_mean: float
    friction_used: float
    drift_per_min: float
    information: float
    information_fraction: float
    z_stat: float
    decision: Decision

    @property
    def n_trades(self) -> int:
        return len(self.trades)

    @property
    def trigger_rate(self) -> float:
        """Séances où la règle s'est déclenchée au moins une fois."""
        if not self.n_scanned:
            return 0.0
        return len({t.day for t in self.trades}) / self.n_scanned

    @property
    def entries_per_session(self) -> float:
        """Entrées par séance retenue — la cadence réellement obtenue."""
        return self.n_trades / self.n_scanned if self.n_scanned else 0.0

    @property
    def mean_net(self) -> float:
        return _mean([t.net_points for t in self.trades])

    @property
    def sd_net(self) -> float:
        return _sd([t.net_points for t in self.trades])

    @property
    def sharpe_trade(self) -> float:
        sd = self.sd_net
        return self.mean_net / sd if sd > 0 else 0.0

    @property
    def hit_rate(self) -> float:
        if not self.trades:
            return 0.0
        return sum(1 for t in self.trades if t.net_points > 0) / self.n_trades

    @property
    def mean_exposure(self) -> float:
        return _mean([t.exposure_min for t in self.trades])

    @property
    def stop_rate(self) -> float:
        if not self.trades:
            return 0.0
        return sum(1 for t in self.trades if t.stopped) / self.n_trades

    @property
    def mean_bps(self) -> float:
        """Dérive nette moyenne par trade, en points de base de l'indice."""
        if not self.trades:
            return 0.0
        return 1e4 * _mean([t.net_points / t.entry_price for t in self.trades])


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _sd(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def measure(sessions: list[Session], config_key: str = "C1",
            protocol: Protocol = PROTOCOL,
            friction_quantile: float = 0.50,
            gamma: dict[str, float] | None = None,
            fill: str = "stop") -> Measurement:
    """Applique une configuration pré-enregistrée à l'historique fourni.

    `config_key` passe par `alp1.prereg.spend`, qui refuse toute configuration
    hors budget : on ne peut pas mesurer une variante qui n'a pas été scellée.
    La friction n'est pas posée mais tirée de la loi déduite, au quantile
    demandé — la médiane pour la mesure, le quantile 90 % pour les règles
    d'arrêt, comme le protocole l'exige.

    `fill` est passé tel quel à `scan_session` : ``"stop"`` pour le
    remplissage optimiste du protocole, ``"extreme"`` pour son pire cas. La
    mesure doit être rendue sous les deux, et `bounds` s'en charge.
    """
    config = spend(config_key)
    if config.key == "C2" and gamma is None:
        raise ValueError(
            "la configuration C2 exige un fichier de gamma net quotidien")

    window = WINDOW_OPEN[config.key]
    trades: list[Trade] = []
    clusters: list[tuple[float, float]] = []
    sigmas: list[float] = []
    frictions: list[float] = []
    scanned = 0

    for i, session in enumerate(sessions):
        sigma_hat = _rolling_sigma(sessions, i)
        if sigma_hat is None:
            continue
        if config.key == "C2":
            g = gamma.get(session.day) if gamma else None
            if g is None or g >= 0.0:
                continue
        scanned += 1
        sigmas.append(sigma_hat)
        # La part des sorties au stop entre dans la loi de friction ; elle est
        # prise au modèle et non aux trades, qui n'existent pas encore. L'écart
        # entre les deux est rapporté par `Measurement.stop_rate`.
        law = friction_law(sigma_hat, p_stop_exit=MODEL_STOP_RATE,
                           size_contracts=1.0, venue=RETAIL_ES)
        friction = law.quantile(friction_quantile)
        frictions.append(friction)
        found = scan_session(session, sigma_hat, window, friction, fill=fill)
        trades.extend(found)
        if found:
            w = 1.0 / (sigma_hat * sigma_hat)
            clusters.append((sum(w * t.net_points for t in found),
                             sum(w * t.exposure_min for t in found)))

    stat = _statistic(clusters)
    frac = stat["information"] / SEALED_MAX_INFORMATION
    return Measurement(
        config_key=config.key, n_sessions=len(sessions), n_scanned=scanned,
        trades=tuple(trades), sigma_hat_mean=_mean(sigmas),
        friction_used=_mean(frictions),
        drift_per_min=stat["drift"], information=stat["information"],
        information_fraction=frac, z_stat=stat["z"],
        decision=decide(protocol, stat["z"], frac, scanned),
    )


@dataclass(frozen=True)
class Bounds:
    """La même mesure sous les deux remplissages du stop, et son verdict.

    Des barres d'une minute ne disent pas à quel prix un stop touché à
    l'intérieur d'une barre a été exécuté. Le protocole retient le niveau du
    stop, ce qui est optimiste ; l'extrême de la barre est le pire compatible
    avec ce qu'on observe. Le prix réel est entre les deux, et rien dans la
    donnée ne dit où.

    L'encadrement se lit d'une seule façon. Si les deux bornes tombent du même
    côté du seuil, la conclusion ne dépend pas de ce qu'on ignore, et elle
    tient. Si elles l'encadrent, **la mesure sur barres ne conclut pas** : il
    faut du tick, et aucune finesse d'analyse ne remplacera la donnée
    manquante. Publier la borne optimiste seule reviendrait à présenter comme
    une mesure ce qui est une hypothèse d'exécution.
    """

    optimistic: Measurement
    worst: Measurement
    threshold: float                 # sur l'espérance **nette**, donc zéro

    @property
    def spread_points(self) -> float:
        """Écart d'espérance nette entre les deux remplissages, en points."""
        return self.optimistic.mean_net - self.worst.mean_net

    @property
    def spread_fraction(self) -> float:
        """Cet écart rapporté à l'espérance optimiste."""
        m = self.optimistic.mean_net
        return self.spread_points / abs(m) if m else float("inf")

    @property
    def straddles(self) -> bool:
        """Le seuil tombe-t-il entre les deux bornes ?"""
        return self.worst.mean_net <= self.threshold < self.optimistic.mean_net

    @property
    def conclusive(self) -> bool:
        """Les deux bornes tranchent-elles dans le même sens ?"""
        return not self.straddles

    @property
    def verdict(self) -> str:
        if self.straddles:
            return ("indécis : le seuil tombe entre les deux remplissages, "
                    "la mesure sur barres ne conclut pas")
        if self.worst.mean_net > self.threshold:
            return "franchi sous les deux remplissages"
        return "non franchi sous les deux remplissages"


def bounds(sessions: list[Session], config_key: str = "C1",
           protocol: Protocol = PROTOCOL,
           friction_quantile: float = 0.50,
           gamma: dict[str, float] | None = None,
           threshold: float | None = None) -> Bounds:
    """Rejoue la mesure sous les deux remplissages du stop et encadre.

    `threshold` est le seuil auquel l'espérance se compare. Il vaut **zéro**
    par défaut, et non le quantile de friction : `Trade.net_points` retranche
    déjà la friction, de sorte que comparer une espérance nette à la friction
    la compterait deux fois. Le seuil d'un critère maître écrit sur le brut se
    passe explicitement.

    Rejouer coûte exactement un second passage : la règle, la friction et la
    fenêtre sont identiques, seul le prix de sortie des trades arrêtés change.
    """
    opt = measure(sessions, config_key, protocol, friction_quantile,
                  gamma, fill="stop")
    bad = measure(sessions, config_key, protocol, friction_quantile,
                  gamma, fill="extreme")
    return Bounds(optimistic=opt, worst=bad,
                  threshold=0.0 if threshold is None else threshold)


def _statistic(clusters: list[tuple[float, float]]) -> dict[str, float]:
    """La statistique principale du protocole, à partir des grappes de date.

    Chaque date apporte ``(A, B) = (Σ w·R, Σ w·τ)`` avec ``w = 1/σ̂²``. La
    dérive nette par minute vaut ``µ̂ = ΣA/ΣB``, et sa variance se lit sur les
    résidus **de date** — ``V = Σ_d (A_d − µ̂·B_d)²`` — sans modèle de
    corrélation entre marchés ni entre entrées d'une même séance. C'est ce qui
    permet au protocole d'être valide sans rien supposer de cette corrélation.
    """
    if len(clusters) < 2:
        return {"drift": 0.0, "information": 0.0, "z": 0.0}
    b_total = sum(b for _, b in clusters)
    if b_total <= 0.0:
        return {"drift": 0.0, "information": 0.0, "z": 0.0}
    mu = sum(a for a, _ in clusters) / b_total
    v = sum((a - mu * b) ** 2 for a, b in clusters)
    if v <= 0.0:
        return {"drift": mu, "information": 0.0, "z": 0.0}
    information = (b_total * b_total) / v
    return {"drift": mu, "information": information,
            "z": mu * math.sqrt(information)}


# --- Tests 3 et 4 : conditionnement et stabilité -----------------------------


@dataclass(frozen=True)
class Split:
    """Un sous-groupe de trades et ses statistiques."""

    label: str
    n: int
    mean_net: float
    sd_net: float

    @property
    def sharpe(self) -> float:
        return self.mean_net / self.sd_net if self.sd_net > 0 else 0.0

    @property
    def t_stat(self) -> float:
        return self.sharpe * math.sqrt(self.n) if self.n > 0 else 0.0


def _split(label: str, trades: list[Trade]) -> Split:
    xs = [t.net_points for t in trades]
    return Split(label, len(xs), _mean(xs), _sd(xs))


def by_gamma(m: Measurement, gamma: dict[str, float]) -> list[Split]:
    """Test 3 — la dérive captée diffère-t-elle selon le signe du gamma net ?"""
    neg = [t for t in m.trades if gamma.get(t.day, 0.0) < 0.0]
    pos = [t for t in m.trades if gamma.get(t.day, 0.0) >= 0.0]
    return [_split("Gamma net négatif", neg), _split("Gamma net positif", pos)]


def by_half_hour(m: Measurement) -> list[Split]:
    """Test 4 — répartition de la dérive captée par tranche d'une demi-heure."""
    buckets: dict[int, list[Trade]] = {}
    for t in m.trades:
        buckets.setdefault(t.entry_minute // 30, []).append(t)
    out = []
    for b in sorted(buckets):
        start = 9 * 60 + 30 + b * 30
        out.append(_split(f"{start // 60:02d}:{start % 60:02d}", buckets[b]))
    return out


def concentration(splits: list[Split]) -> float:
    """Part du résultat total portée par la meilleure tranche.

    Proche de 1 : tout vient d'une tranche, et le protocole retient la
    sélection plutôt que la structure. Proche de la part de temps de la
    tranche : la dérive est distribuée, ce qui est le seul cas où l'effet
    ressemble à ce que la littérature décrit.
    """
    totals = [s.n * s.mean_net for s in splits]
    gross = sum(abs(x) for x in totals)
    return max(totals) / gross if gross > 0 else 0.0


# --- Enchaînement complet ----------------------------------------------------


@dataclass(frozen=True)
class Stage:
    """Une étape du protocole : ce qui est mesuré, le critère, l'issue."""

    number: int
    name: str
    measured: str
    criterion: str
    passed: bool
    halts: bool


@dataclass(frozen=True)
class ProtocolRun:
    """L'exécution complète, étape par étape, avec ses interruptions."""

    stages: tuple[Stage, ...]
    measurement: Measurement | None

    @property
    def halted_at(self) -> Stage | None:
        for s in self.stages:
            if s.halts:
                return s
        return None

    @property
    def completed(self) -> bool:
        return self.halted_at is None


def run_protocol(sessions: list[Session], gamma: dict[str, float] | None = None,
                 protocol: Protocol = PROTOCOL,
                 null_draws: int = 8) -> ProtocolRun:
    """Enchaîne les tests dans l'ordre pré-enregistré, arrêts compris.

    Le premier étage mesure la **loi d'échelle**, et non plus seulement la
    fréquence de cassure. C'est ce que le document annonçait sans que le code
    sache le faire : l'exposant décide de σ₁, de la bande, du stop, de
    l'exposition et du seuil de signal, donc il précède tout le reste. Il est
    mesuré par ratio de variance, rapporté à la loi nulle simulée de
    l'estimateur — sans quoi une martingale passerait pour persistante.
    """
    stages: list[Stage] = []

    nulls = null_grid(n_sessions=min(len(sessions), 250), draws=null_draws)
    sc = hurst_regression(sessions, nulls=nulls)
    ecarts = []
    for r in scan(sessions):
        ecarts.append(abs(r.z_null(nulls[r.q])))
    z_max = max(ecarts) if ecarts else 0.0
    diffusif = abs(sc.hurst - 0.5) < 0.02
    stages.append(Stage(
        0, "Loi d'échelle",
        f"Ĥ = {sc.hurst:.4f} corrigé de la loi nulle (R² {sc.r2:.4f}), "
        f"écart maximal à la nulle {z_max:.2f} σ",
        "l'exposant mesuré remplace celui posé ; H = 0,50 ferme le régime "
        "de gamma comme explication",
        True, False))

    m = measure(sessions, "C1", protocol)

    rate_ok = m.trigger_rate >= 0.5
    stages.append(Stage(
        1, "Fréquence de cassure",
        f"{100 * m.trigger_rate:.1f} % des séances déclenchent, "
        f"{m.entries_per_session:.2f} entrée(s) par séance",
        "au moins une séance sur deux", rate_ok, not rate_ok))
    if not rate_ok:
        return ProtocolRun(tuple(stages), m)

    strict = friction_law(m.sigma_hat_mean, MODEL_STOP_RATE).quantile(0.90)
    net_strict = m.mean_net - (strict - m.friction_used)
    drift_ok = net_strict > 0.0
    stages.append(Stage(
        2, "Dérive captée",
        f"{m.mean_net:+.3f} pt par trade ({m.mean_bps:+.2f} pb), "
        f"soit {net_strict:+.3f} pt à la friction du quantile 90 %",
        f"positive à la friction du quantile 90 % ({strict:.3f} pt contre "
        f"{m.friction_used:.3f} pt à la médiane)",
        drift_ok, not drift_ok))
    if not drift_ok:
        return ProtocolRun(tuple(stages), m)

    if gamma is not None:
        splits = by_gamma(m, gamma)
        gap = splits[0].mean_net - splits[1].mean_net
        stages.append(Stage(
            3, "Conditionnement gamma",
            f"écart de {gap:+.3f} pt entre gamma négatif et positif",
            "écart non nul pour conserver le filtre", abs(gap) > 0.0, False))

    hours = by_half_hour(m)
    conc = concentration(hours)
    stages.append(Stage(
        4, "Heure d'entrée",
        f"concentration de {100 * conc:.1f} % sur la meilleure tranche",
        "en dessous de 60 % pour écarter la sélection", conc < 0.6, False))

    stages.append(Stage(
        5, "Décision pré-enregistrée",
        f"Z = {m.z_stat:+.3f} à {100 * m.information_fraction:.1f} % de "
        f"l'information maximale, sur {m.n_trades} trades",
        m.decision.reason, m.decision.rejected, False))
    return ProtocolRun(tuple(stages), m)


def format_run(run: ProtocolRun) -> str:
    """Rend l'exécution sous forme lisible, sans interprétation ajoutée."""
    lines = []
    for s in run.stages:
        mark = "ok " if s.passed else "NON"
        lines.append(f"  [{mark}] Test {s.number} — {s.name}")
        lines.append(f"         mesuré : {s.measured}")
        lines.append(f"         critère : {s.criterion}")
        if s.halts:
            lines.append("         → le protocole s'arrête ici.")
    m = run.measurement
    if m is not None and m.n_trades:
        lines.append("")
        lines.append(f"  {m.n_trades} trades sur {m.n_scanned} séances, "
                     f"σ̂₁ moyenne {m.sigma_hat_mean:.2f} pt, "
                     f"friction {m.friction_used:.3f} pt")
        lines.append(f"  net moyen {m.mean_net:+.3f} pt ({m.mean_bps:+.2f} pb), "
                     f"SR/trade {m.sharpe_trade:+.4f}, "
                     f"réussite {100 * m.hit_rate:.1f} %, "
                     f"stop {100 * m.stop_rate:.1f} %, "
                     f"exposition {m.mean_exposure:.0f} min")
        lines.append(f"  dérive nette {m.drift_per_min:+.5f} pt/min, "
                     f"information {m.information:.0f} "
                     f"({100 * m.information_fraction:.1f} % de I_max), "
                     f"Z = {m.z_stat:+.3f}")
        lines.append(f"  décision : {m.decision.reason}")
    return "\n".join(lines)


def main(path: str | None = None, gamma_path: str | None = None) -> None:
    import sys

    from .dataset import audit, load_csv, load_gamma_csv, synthetic_sessions

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = path or (args[0] if args else None)
    gamma_path = gamma_path or (args[1] if len(args) > 1 else None)

    if path is None:
        print("usage : python main.py --measure <prix.csv> [gamma.csv]\n")
        print("Aucun fichier fourni — la chaîne est exécutée sur une série")
        print("synthétique sans dérive, dont la réponse est connue d'avance :")
        print("le protocole doit refuser.\n")
        sessions = synthetic_sessions(260)
        gamma = None
    else:
        sessions = load_csv(path)
        a = audit(sessions)
        print(f"Historique : {a.n_sessions} séances du {a.first_day} au "
              f"{a.last_day}, {100 * a.completeness:.1f} % des minutes")
        for p in a.problems():
            print(f"  — {p}")
        if not a.usable:
            print("\nFichier inexploitable en l'état : la mesure n'est pas "
                  "conduite.")
            return
        gamma = load_gamma_csv(gamma_path) if gamma_path else None

    print(format_run(run_protocol(sessions, gamma)))


if __name__ == "__main__":
    main()
