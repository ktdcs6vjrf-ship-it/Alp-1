"""Lecture et audit d'un historique de prix à la minute.

Le dépôt ne contient aucune donnée de marché, et c'est sa limite principale.
Ce module est la moitié manquante : il définit **exactement** ce qu'il faut
fournir, le lit, et refuse de le mesurer tant qu'il n'est pas propre.

Le format attendu est le plus banal qui soit — un CSV de barres d'une minute :

    timestamp,open,high,low,close,volume
    2026-01-02 09:30:00,5901.25,5903.50,5900.75,5902.00,1843

Les seules exigences sont celles qui ont des conséquences sur la mesure :

  - **Horodatage en heure de l'échange** (ET), pas en UTC ni en heure locale.
    Une séance décalée d'une heure déplace la bande de bruit et fausse toutes
    les cassures. Le module vérifie que les séances commencent bien à
    l'ouverture déclarée et refuse le fichier sinon.
  - **Barres régulières d'une minute**, séance régulière uniquement (09:30 à
    16:00 ET). Les barres hors séance sont écartées, pas fusionnées.
  - **Prix du contrat continu, ajustés aux roulements**, ou un seul contrat à
    la fois. Un saut de roulement non ajusté est un faux mouvement de plusieurs
    points, exactement à l'échelle du signal recherché.

L'audit ne juge pas la qualité de la source ; il compte ce qui manque. Une
séance amputée, un doublon d'horodatage, un volume nul sur une barre en séance
sont des faits, et chacun a un effet connu sur la mesure : le module les
rapporte, et `Audit.usable` décide.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime, timedelta

SESSION_OPEN = (9, 30)
SESSION_CLOSE = (16, 0)
SESSION_MINUTES = 390

_TS_KEYS = ("timestamp", "datetime", "date_time", "time", "date")
_OHLC_KEYS = {"open": ("open", "o"), "high": ("high", "h"),
              "low": ("low", "l"), "close": ("close", "c", "last")}
_VOL_KEYS = ("volume", "vol", "v", "qty")


@dataclass(frozen=True)
class Bar:
    """Une barre d'une minute, ramenée à sa position dans la séance."""

    day: str
    minute: int          # minutes écoulées depuis l'ouverture, 0 = 09:30
    open: float
    high: float
    low: float
    close: float
    volume: float

    @property
    def valid(self) -> bool:
        return (self.low <= min(self.open, self.close)
                and self.high >= max(self.open, self.close)
                and self.low <= self.high)


@dataclass(frozen=True)
class Session:
    """Une séance régulière, ses barres ordonnées par minute."""

    day: str
    bars: tuple[Bar, ...]

    @property
    def n_bars(self) -> int:
        return len(self.bars)

    @property
    def open_price(self) -> float:
        return self.bars[0].open

    @property
    def close_price(self) -> float:
        return self.bars[-1].close

    @property
    def net_move(self) -> float:
        """Déplacement ouverture → clôture, en points. La grandeur qui calibre."""
        return self.close_price - self.open_price

    @property
    def range_points(self) -> float:
        return max(b.high for b in self.bars) - min(b.low for b in self.bars)

    def bar_at(self, minute: int) -> Bar | None:
        for b in self.bars:
            if b.minute == minute:
                return b
        return None

    def bars_from(self, minute: int) -> tuple[Bar, ...]:
        return tuple(b for b in self.bars if b.minute >= minute)

    def vwap(self) -> float:
        num = sum(0.25 * (b.open + b.high + b.low + b.close) * b.volume
                  for b in self.bars)
        den = sum(b.volume for b in self.bars)
        if den <= 0:
            return sum(b.close for b in self.bars) / len(self.bars)
        return num / den


# --- Lecture ----------------------------------------------------------------


def _pick(fieldnames: list[str], candidates) -> str | None:
    lowered = {f.strip().lower(): f for f in fieldnames}
    for c in candidates:
        if c in lowered:
            return lowered[c]
    return None


def _parse_timestamp(raw: str) -> datetime:
    """Accepte l'ISO 8601 usuel, l'espace au lieu du T, et l'epoch en secondes.

    Les formats ambigus en jour et mois sont refusés plutôt que devinés : une
    inversion silencieuse déplace tout l'historique sans lever la moindre
    erreur, et le résultat de la mesure resterait plausible.
    """
    s = raw.strip()
    if not s:
        raise ValueError("horodatage vide")
    if s.replace(".", "", 1).isdigit() and len(s.split(".")[0]) >= 9:
        return datetime.utcfromtimestamp(float(s))
    s = s.replace("Z", "").replace("z", "")
    if "+" in s[10:]:
        s = s[:10] + s[10:].split("+")[0]
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
                    "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M"):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
    raise ValueError(
        f"horodatage illisible : {raw!r}. Les formats à barres obliques "
        "commençant par le jour ou le mois — 01/02/2026 — sont refusés et non "
        "devinés : 01/02 est le 1er février pour la moitié du monde et le "
        "2 janvier pour l'autre, et se tromper décale tout l'historique sans "
        "produire la moindre erreur visible. Convertir en ISO 8601 "
        "(2026-02-01 09:31:00) avant de charger.")


def _minute_of_session(ts: datetime) -> int:
    return (ts.hour * 60 + ts.minute) - (SESSION_OPEN[0] * 60 + SESSION_OPEN[1])


def load_csv(path: str, session_open: tuple[int, int] = SESSION_OPEN,
             session_minutes: int = SESSION_MINUTES) -> list[Session]:
    """Charge un CSV de barres d'une minute et le découpe en séances.

    Les colonnes sont reconnues par leur nom, quel que soit leur ordre et leur
    casse ; un fichier à colonnes `date` et `time` séparées est accepté. Les
    barres hors de la fenêtre `[ouverture, ouverture + durée[` sont écartées
    silencieusement — c'est le seul filtrage automatique, et il est explicite
    dans le compte de l'audit.
    """
    open_min = session_open[0] * 60 + session_open[1]
    by_day: dict[str, dict[int, Bar]] = {}

    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError("fichier sans en-tête")
        names = list(reader.fieldnames)
        ts_col = _pick(names, _TS_KEYS)
        if ts_col is None:
            raise ValueError(
                "aucune colonne d'horodatage : attendu l'un de "
                f"{', '.join(_TS_KEYS)}")
        time_col = _pick(names, ("time",)) if ts_col.strip().lower() == "date" else None
        cols = {k: _pick(names, v) for k, v in _OHLC_KEYS.items()}
        missing = [k for k, v in cols.items() if v is None]
        if missing:
            raise ValueError(f"colonnes manquantes : {', '.join(missing)}")
        vol_col = _pick(names, _VOL_KEYS)

        for row in reader:
            raw = row[ts_col]
            if time_col and row.get(time_col):
                raw = f"{raw.strip()} {row[time_col].strip()}"
            ts = _parse_timestamp(raw)
            minute = (ts.hour * 60 + ts.minute) - open_min
            if not 0 <= minute < session_minutes:
                continue
            day = ts.strftime("%Y-%m-%d")
            bar = Bar(
                day=day, minute=minute,
                open=float(row[cols["open"]]), high=float(row[cols["high"]]),
                low=float(row[cols["low"]]), close=float(row[cols["close"]]),
                volume=float(row[vol_col]) if vol_col and row.get(vol_col) else 0.0,
            )
            by_day.setdefault(day, {})[minute] = bar

    return [Session(day, tuple(sorted(bars.values(), key=lambda b: b.minute)))
            for day, bars in sorted(by_day.items())]


def load_gamma_csv(path: str) -> dict[str, float]:
    """Charge un fichier `date,gamma_net` — un niveau publié par séance.

    Seul le **signe** entre dans le protocole ; la valeur est conservée pour
    permettre un tri par intensité au cas où le signe seul ne sépare rien.
    """
    out: dict[str, float] = {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError("fichier sans en-tête")
        names = list(reader.fieldnames)
        date_col = _pick(names, ("date", "day", "timestamp"))
        val_col = _pick(names, ("gamma_net", "net_gamma", "gamma", "gex", "value"))
        if date_col is None or val_col is None:
            raise ValueError("attendu deux colonnes : date et gamma_net")
        for row in reader:
            ts = _parse_timestamp(row[date_col])
            out[ts.strftime("%Y-%m-%d")] = float(row[val_col])
    return out


# --- Audit ------------------------------------------------------------------


@dataclass(frozen=True)
class Audit:
    """Ce que l'historique contient, et ce qui lui manque."""

    n_sessions: int
    n_bars: int
    expected_bars: int
    first_day: str
    last_day: str
    short_sessions: tuple[str, ...]
    late_open: tuple[str, ...]
    invalid_bars: int
    zero_volume_bars: int
    has_volume: bool
    max_gap_days: int

    @property
    def completeness(self) -> float:
        return self.n_bars / self.expected_bars if self.expected_bars else 0.0

    @property
    def usable(self) -> bool:
        """Le fichier est-il exploitable pour la mesure ?

        Les trois refus sont ceux qui faussent la mesure au lieu de la bruiter :
        une couverture inférieure à 95 % des minutes attendues, des séances
        ouvrant trop tard (horodatage probablement en UTC), ou des barres
        incohérentes.
        """
        return (self.completeness >= 0.95
                and not self.late_open
                and self.invalid_bars == 0)

    def problems(self) -> list[str]:
        out = []
        if self.completeness < 0.95:
            out.append(
                f"couverture de {100 * self.completeness:.1f} % des minutes "
                f"attendues ({self.n_bars} sur {self.expected_bars})")
        if self.late_open:
            out.append(
                f"{len(self.late_open)} séance(s) n'ouvrant pas à l'heure "
                f"déclarée — horodatage probablement en UTC : "
                f"{', '.join(self.late_open[:3])}…")
        if self.invalid_bars:
            out.append(f"{self.invalid_bars} barre(s) incohérente(s) "
                       "(haut < clôture, bas > ouverture, etc.)")
        if self.short_sessions:
            out.append(f"{len(self.short_sessions)} séance(s) écourtée(s) — "
                       "demi-séances de veille de jour férié, en général")
        if not self.has_volume:
            out.append("aucun volume : les tests de profil de volume sont "
                       "indisponibles, les autres non affectés")
        return out


def audit(sessions: list[Session],
          session_minutes: int = SESSION_MINUTES,
          min_bars: int = 300) -> Audit:
    """Compte ce qui manque, sans rien corriger."""
    if not sessions:
        raise ValueError("historique vide")
    n_bars = sum(s.n_bars for s in sessions)
    invalid = sum(1 for s in sessions for b in s.bars if not b.valid)
    zero_vol = sum(1 for s in sessions for b in s.bars if b.volume == 0.0)
    has_vol = any(b.volume > 0 for s in sessions for b in s.bars)
    short = tuple(s.day for s in sessions if s.n_bars < min_bars)
    late = tuple(s.day for s in sessions if s.bars[0].minute > 15)

    days = [datetime.strptime(s.day, "%Y-%m-%d") for s in sessions]
    gap = 0
    for a, b in zip(days, days[1:]):
        gap = max(gap, (b - a).days)

    return Audit(
        n_sessions=len(sessions), n_bars=n_bars,
        expected_bars=len(sessions) * session_minutes,
        first_day=sessions[0].day, last_day=sessions[-1].day,
        short_sessions=short, late_open=late,
        invalid_bars=invalid, zero_volume_bars=zero_vol,
        has_volume=has_vol, max_gap_days=gap,
    )


# --- Séries synthétiques : pour tester la chaîne sans données ---------------


def synthetic_sessions(n_days: int, sigma_per_min: float = 3.04,
                       drift_points_per_min: float = 0.0,
                       momentum_points_per_min: float = 0.0,
                       index_level: float = 6000.0,
                       seed: int = 20260821,
                       session_minutes: int = SESSION_MINUTES,
                       ) -> list[Session]:
    """Historique simulé, de vérité connue, au format exact du lecteur.

    Il ne remplace aucune donnée de marché et ne mesure rien du marché. Son
    seul rôle est de **tester la chaîne de mesure** : si la chaîne, appliquée à
    une série dont la vérité est connue, ne la retrouve pas, le défaut est dans
    la chaîne. C'est le contrôle qu'un historique réel ne permet pas, puisqu'on
    n'y connaît pas la réponse.

    Deux dérives, et la distinction est le cœur du sujet.
    `drift_points_per_min` est une dérive **inconditionnelle**, la même quel
    que soit l'état de la séance ; une règle de cassure ne la capte presque
    pas, puisqu'elle prend position dans les deux sens et n'est longue qu'un
    peu plus d'une fois sur deux. `momentum_points_per_min` est une dérive
    **conditionnelle au signe du déplacement depuis l'ouverture** — c'est la
    forme exacte de l'effet que la littérature documente, et la seule qu'une
    cassure de bande puisse capter.

    Un contrôle qui n'injecterait que la première conclurait que la chaîne ne
    mesure rien ; il aurait tort, et c'est une erreur facile à commettre.
    """
    from .mc import Rng

    rng = Rng(seed)
    sessions: list[Session] = []
    price = index_level
    start = datetime(2026, 1, 5)
    day = 0
    while len(sessions) < n_days:
        d = start + timedelta(days=day)
        day += 1
        if d.weekday() >= 5:
            continue
        bars = []
        p = price
        session_open_price = p
        for m in range(session_minutes):
            o = p
            displacement = o - session_open_price
            sign = 0.0 if displacement == 0.0 else math.copysign(1.0, displacement)
            step = (drift_points_per_min
                    + momentum_points_per_min * sign
                    + sigma_per_min * rng.gauss())
            c = o + step
            wick = abs(sigma_per_min * rng.gauss()) * 0.25
            bars.append(Bar(
                day=d.strftime("%Y-%m-%d"), minute=m,
                open=o, high=max(o, c) + wick, low=min(o, c) - wick,
                close=c, volume=1000.0 + 200.0 * abs(rng.gauss()),
            ))
            p = c
        sessions.append(Session(d.strftime("%Y-%m-%d"), tuple(bars)))
        price = p
    return sessions


def write_csv(sessions: list[Session], path: str) -> None:
    """Écrit un historique au format attendu — sert de fichier d'exemple."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        for s in sessions:
            for b in s.bars:
                hh, mm = divmod(SESSION_OPEN[0] * 60 + SESSION_OPEN[1] + b.minute, 60)
                w.writerow([f"{s.day} {hh:02d}:{mm:02d}:00",
                            f"{b.open:.2f}", f"{b.high:.2f}", f"{b.low:.2f}",
                            f"{b.close:.2f}", f"{b.volume:.0f}"])


def session_dispersion(sessions: list[Session]) -> float:
    """Écart-type du déplacement ouverture → clôture, en points.

    C'est **le** nombre que le document pose et que l'historique remplacerait :
    toute la calibration en découle, `σ₁ = dispersion/√durée`. Le mesurer est
    le premier usage d'un fichier de prix, avant tout signal.
    """
    moves = [s.net_move for s in sessions]
    if len(moves) < 2:
        raise ValueError("au moins deux séances requises")
    mean = sum(moves) / len(moves)
    var = sum((m - mean) ** 2 for m in moves) / (len(moves) - 1)
    return math.sqrt(var)


def main(path: str | None = None) -> None:
    import sys

    path = path or (sys.argv[1] if len(sys.argv) > 1 else None)
    if path is None:
        print("usage : python -m alp1.dataset <fichier.csv>")
        print("\nAucun fichier fourni — démonstration sur série synthétique.\n")
        sessions = synthetic_sessions(60)
    else:
        sessions = load_csv(path)

    a = audit(sessions)
    print(f"Séances : {a.n_sessions} du {a.first_day} au {a.last_day}")
    print(f"Barres  : {a.n_bars} sur {a.expected_bars} attendues "
          f"({100 * a.completeness:.1f} %)")
    print(f"Dispersion de séance mesurée : {session_dispersion(sessions):.2f} pt")
    print(f"Exploitable : {'oui' if a.usable else 'NON'}")
    for p in a.problems():
        print(f"  — {p}")


if __name__ == "__main__":
    main()
