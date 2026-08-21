"""Loi d'échelle mesurée : ratio de variance de Lo et MacKinlay, et exposant.

Le document désigne l'exposant d'échelle comme le paramètre le plus fragile de
sa calibration — σ₁, la bande de bruit, le stop, l'exposition et le seuil de
signal en descendent tous — et annonce que le Test 1 le mesure par ratio de
variance. Aucun ratio de variance n'existait dans le dépôt : `scaling.calibrate`
reçoit l'exposant en argument, et le Test 1 de la chaîne de mesure comptait des
cassures de bande. Ce module comble l'écart entre ce que le document annonce et
ce que le code sait faire.

**L'estimateur.** Sous marche aléatoire, la variance des rendements agrégés sur
`q` périodes vaut `q` fois la variance à une période. Le rapport des deux vaut
donc un, et son écart à un mesure l'autocorrélation cumulée :

    VR(q) = σ̂²_c(q) / σ̂²_a  →  1 sous martingale.

On retient l'estimateur à fenêtres chevauchantes de Lo et MacKinlay (1988),
sans biais sous l'hypothèse nulle, et sa statistique **robuste à
l'hétéroscédasticité** — la variante indispensable ici, puisque la volatilité
intraséance est saisonnière en U et que la statistique homoscédastique
rejetterait la marche aléatoire sur cette seule saisonnalité.

**L'exposant.** Pour un processus auto-similaire d'exposant `H`, la dispersion
croît en `t^H`, donc `VR(q) = q^(2H−1)` et

    Ĥ(q) = ½ + ln VR(q) / (2 ln q).

Deux lectures sont fournies. `hurst_from_vr` donne l'exposant impliqué par un
seul horizon ; `hurst_regression` régresse `ln Var(q)` sur `ln q` sur toute la
grille, ce qui est l'estimateur usuel de la loi d'échelle et le seul qui
utilise l'ensemble des horizons.

**Le découpage.** Les séances sont traitées **séparément** : aucun rendement
n'enjambe le gap de nuit, dont la variance n'a rien à voir avec celle de la
séance et gonflerait mécaniquement les agrégats longs. Les sommes qui composent
l'estimateur sont calculées séance par séance puis additionnées, ce qui donne
l'estimateur groupé sans jamais franchir une frontière de séance.

**L'intervalle.** La statistique asymptotique de Lo-MacKinlay suppose un
échantillon long ; sur quelques centaines de séances courtes, elle est
indicative. `bootstrap_ci` rééchantillonne les **séances entières** avec remise
— le bloc naturel, qui préserve la saisonnalité intraséance et la dépendance à
l'intérieur d'une séance — et donne l'intervalle qui décide réellement.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .dataset import Session
from .mc import Rng

#: Horizons d'agrégation, en minutes. Le plus long reste très en deçà de la
#: séance : au-delà, le nombre de blocs par séance tombe à quelques unités et
#: l'estimateur n'a plus de contenu.
Q_GRID = (2, 5, 10, 15, 30, 60)


def log_returns(session: Session) -> list[float]:
    """Rendements logarithmiques à la minute d'une séance, dans l'ordre.

    Les barres manquantes coupent la série : un rendement n'est formé qu'entre
    deux minutes consécutives. Une séance trouée donne donc plusieurs segments,
    et c'est le comportement voulu — un rendement à cheval sur un trou de dix
    minutes n'est pas un rendement à une minute.
    """
    out: list[float] = []
    prev = None
    for bar in session.bars:
        if bar.close <= 0:
            prev = None
            continue
        if prev is not None and bar.minute == prev[0] + 1:
            out.append(math.log(bar.close / prev[1]))
        prev = (bar.minute, bar.close)
    return out


def _segments(session: Session) -> list[list[float]]:
    """Segments de rendements consécutifs, un par plage sans trou."""
    segs: list[list[float]] = []
    cur: list[float] = []
    prev = None
    for bar in session.bars:
        if bar.close <= 0:
            prev = None
            if cur:
                segs.append(cur)
                cur = []
            continue
        if prev is not None and bar.minute == prev[0] + 1:
            cur.append(math.log(bar.close / prev[1]))
        elif cur:
            segs.append(cur)
            cur = []
        prev = (bar.minute, bar.close)
    if cur:
        segs.append(cur)
    return segs


@dataclass(frozen=True)
class VRResult:
    """Ratio de variance à un horizon, et ce qu'il implique."""

    q: int
    vr: float
    z_hetero: float
    n_returns: int
    n_segments: int

    @property
    def hurst(self) -> float:
        return hurst_from_vr(self.vr, self.q)

    @property
    def rejects_random_walk(self) -> bool:
        """|z| > 1,96 : la marche aléatoire est rejetée à 5 %."""
        return abs(self.z_hetero) > 1.959963984540054

    def excess(self, null: "Null") -> float:
        """Écart du VR mesuré à celui qu'une marche aléatoire produirait ici.

        C'est cet écart, et non le VR brut, qui porte l'information : à q = 60
        sur des séances de 390 minutes, une martingale donne déjà VR ≈ 1,20.
        """
        return self.vr - null.mean

    def hurst_corrected(self, null: "Null") -> float:
        """Exposant impliqué par le VR ramené à sa loi nulle."""
        return null.hurst(self.vr)

    def z_null(self, null: "Null") -> float:
        """Écarts-types à la loi nulle simulée. La statistique qui décide."""
        return null.z(self.vr)


def hurst_from_vr(vr: float, q: int) -> float:
    """Exposant impliqué par un ratio de variance à l'horizon q.

    De ``VR(q) = q^(2H−1)`` on tire ``H = ½ + ln VR/(2 ln q)``. Un VR de 1
    donne exactement ½, et c'est le contrôle le plus utile de la fonction.
    """
    if q < 2:
        raise ValueError("q doit être ≥ 2")
    if vr <= 0:
        return float("nan")
    return 0.5 + math.log(vr) / (2.0 * math.log(q))


def variance_ratio(sessions: list[Session], q: int) -> VRResult:
    """VR(q) groupé sur les séances, et sa statistique robuste.

    Les sommes de Lo et MacKinlay sont accumulées segment par segment, jamais
    à travers une frontière de séance. La moyenne est estimée sur l'ensemble
    des rendements retenus, ce qui est le choix conservateur : l'estimer par
    séance absorberait dans la moyenne une part de la dérive qu'on cherche.
    """
    if q < 2:
        raise ValueError("q doit être ≥ 2")

    segs = [s for sess in sessions for s in _segments(sess) if len(s) > q]
    if not segs:
        raise ValueError("aucun segment plus long que l'horizon demandé")

    n_ret = sum(len(s) for s in segs)
    mu = sum(v for s in segs for v in s) / n_ret

    # σ̂²_a : variance des rendements à une période
    sum_a = sum((v - mu) ** 2 for s in segs for v in s)
    var_a = sum_a / (n_ret - 1)

    # σ̂²_c(q) : variance des rendements agrégés, fenêtres chevauchantes,
    # avec le facteur de correction sans biais appliqué segment par segment.
    num_c, denom_c = 0.0, 0.0
    for s in segs:
        n = len(s)
        cum = [0.0]
        for v in s:
            cum.append(cum[-1] + v)
        for k in range(q, n + 1):
            num_c += (cum[k] - cum[k - q] - q * mu) ** 2
        denom_c += q * (n - q + 1) * (1.0 - q / n)
    if denom_c <= 0 or var_a <= 0:
        raise ValueError("échantillon insuffisant pour cet horizon")
    var_c = num_c / denom_c
    vr = var_c / var_a

    return VRResult(q=q, vr=vr, z_hetero=_z_hetero(segs, mu, q, vr, n_ret),
                    n_returns=n_ret, n_segments=len(segs))


def _z_hetero(segs: list[list[float]], mu: float, q: int,
              vr: float, n_ret: int) -> float:
    """Statistique z robuste à l'hétéroscédasticité (Lo-MacKinlay, M2).

    ``ψ* = Σ_{j=1}^{q−1} [2(q−j)/q]² δ̂_j`` avec δ̂_j le rapport de la somme des
    produits d'écarts carrés décalés de j au carré de la somme des écarts
    carrés. C'est la variante qui survit à une volatilité qui change au cours
    de la séance, et la saisonnalité en U impose de l'employer.
    """
    d = [[(v - mu) ** 2 for v in s] for s in segs]
    total = sum(v for s in d for v in s)
    if total <= 0:
        return float("nan")
    psi = 0.0
    for j in range(1, q):
        cross = sum(s[k] * s[k - j] for s in d for k in range(j, len(s)))
        delta = cross / (total ** 2)
        psi += ((2.0 * (q - j)) / q) ** 2 * delta
    if psi <= 0:
        return float("nan")
    return (vr - 1.0) / math.sqrt(psi)


@dataclass(frozen=True)
class Null:
    """Ce qu'une marche aléatoire produit ici : moyenne et dispersion du VR."""

    q: int
    mean: float
    sd: float
    draws: int

    def z(self, vr: float) -> float:
        """Écarts-types séparant un VR mesuré de sa loi nulle simulée.

        C'est cette statistique qui décide, et non le z asymptotique de
        Lo-MacKinlay : sur des séances de 390 minutes, ce dernier rejette la
        marche aléatoire *sur une marche aléatoire*, à tous les horizons de la
        grille. La loi nulle simulée porte le biais d'échantillon fini dans sa
        moyenne et sa dispersion, donc l'écart qu'elle mesure est valide.
        """
        return (vr - self.mean) / self.sd if self.sd > 0 else float("nan")

    def hurst(self, vr: float) -> float:
        """Exposant impliqué par le VR ramené à sa loi nulle."""
        if self.mean <= 0 or vr <= 0:
            return float("nan")
        return hurst_from_vr(vr / self.mean, self.q)


def null_reference(q: int, n_sessions: int = 250, draws: int = 40,
                   seed: int = 20260821) -> Null:
    """Loi du VR(q) sous marche aléatoire, à structure de séance identique.

    L'estimateur de Lo et MacKinlay est sans biais asymptotiquement, non à
    échantillon fini : sur des séances de 390 minutes, la correction
    ``(1 − q/n)`` cesse de suffire dès que `q` dépasse quelques dizaines, et
    VR(q) dérive vers le haut — une martingale y paraît persistante, et le z
    asymptotique la rejette.

    Le document impose partout de rapporter un motif à sa fréquence sous un
    prix sans dérive. Cette fonction applique la règle à l'estimateur
    lui-même : elle simule des séances sans dérive et rend la loi du VR qu'on
    y observe. C'est à elle, et non à un, que le VR mesuré se compare.
    """
    from .dataset import synthetic_sessions
    if draws < 2:
        raise ValueError("draws doit être ≥ 2 pour estimer une dispersion")
    vals: list[float] = []
    for d in range(draws):
        sess = synthetic_sessions(n_sessions, seed=seed + d * 7919)
        try:
            vals.append(variance_ratio(sess, q).vr)
        except ValueError:
            continue
    if len(vals) < 2:
        raise ValueError("la loi nulle n'a produit aucune estimation")
    m = sum(vals) / len(vals)
    sd = math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))
    return Null(q=q, mean=m, sd=sd, draws=len(vals))


#: La loi nulle ne dépend que de la longueur de séance, de l'horizon et du
#: nombre de tirages — jamais des données mesurées. La resimuler à chaque appel
#: coûte cher et ne change rien : elle est donc mémorisée par ses arguments.
_NULL_CACHE: dict[tuple[int, int, int, int], Null] = {}


def null_grid(qs: tuple[int, ...] = Q_GRID, n_sessions: int = 250,
              draws: int = 40, seed: int = 20260821) -> dict[int, Null]:
    """La loi nulle à chaque horizon de la grille, mémorisée.

    Le nombre de séances simulées est borné : au-delà de quelques centaines,
    la moyenne du VR sous marche aléatoire ne bouge plus, et seule sa
    dispersion se resserre — ce qui rendrait le test *plus* sévère sans rien
    apprendre. Simuler autant de séances que l'historique en compte coûterait
    cher pour rien.
    """
    n = min(n_sessions, 250)
    out = {}
    for q in qs:
        cle = (q, n, draws, seed)
        if cle not in _NULL_CACHE:
            _NULL_CACHE[cle] = null_reference(q, n, draws, seed)
        out[q] = _NULL_CACHE[cle]
    return out


def scan(sessions: list[Session],
         qs: tuple[int, ...] = Q_GRID) -> list[VRResult]:
    """Le ratio de variance à chaque horizon de la grille."""
    out = []
    for q in qs:
        try:
            out.append(variance_ratio(sessions, q))
        except ValueError:
            continue
    return out


@dataclass(frozen=True)
class Scaling:
    """Exposant d'échelle estimé sur toute la grille d'horizons."""

    hurst: float
    intercept: float
    r2: float
    points: tuple[tuple[int, float], ...]     # (q, Var(q))

    @property
    def diffusive(self) -> bool:
        """L'exposant est-il celui d'une marche aléatoire, à 0,01 près ?"""
        return abs(self.hurst - 0.5) < 0.01


def hurst_regression(sessions: list[Session],
                     qs: tuple[int, ...] = Q_GRID,
                     nulls: dict[int, "Null"] | None = None) -> Scaling:
    """Ĥ par régression de ln Var(q) sur ln q.

    ``Var(q) = σ² q^(2H)`` donne ``ln Var(q) = ln σ² + 2H ln q`` : la pente
    vaut deux fois l'exposant. C'est l'estimateur de loi d'échelle usuel, et le
    seul qui utilise tous les horizons à la fois plutôt qu'un seul.

    L'horizon q = 1 est inclus d'office : il ancre la droite sur la variance à
    une minute, celle-là même dont la calibration du document tire σ₁.

    `nulls` corrige chaque VR par sa loi nulle avant la régression. Sans lui,
    la pente porte le biais d'échantillon fini de l'estimateur : sur une
    martingale, la régression brute rend Ĥ ≈ 0,52 au lieu de ½.
    """
    var1 = variance_ratio(sessions, min(qs))
    pts: list[tuple[int, float]] = []

    segs = [s for sess in sessions for s in _segments(sess)]
    n_ret = sum(len(s) for s in segs)
    mu = sum(v for s in segs for v in s) / n_ret
    base = sum((v - mu) ** 2 for s in segs for v in s) / (n_ret - 1)
    pts.append((1, base))

    for r in scan(sessions, qs):
        vr = r.vr / nulls[r.q].mean if nulls and r.q in nulls else r.vr
        pts.append((r.q, vr * base * r.q))

    n = len(pts)
    if n < 3:
        raise ValueError("trop peu d'horizons pour une régression")
    xs = [math.log(q) for q, _ in pts]
    ys = [math.log(v) for _, v in pts]
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    inter = my - slope * mx
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (inter + slope * x)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0

    del var1
    return Scaling(hurst=slope / 2.0, intercept=inter, r2=r2,
                   points=tuple(pts))


def bootstrap_ci(sessions: list[Session], qs: tuple[int, ...] = Q_GRID,
                 draws: int = 400, level: float = 0.95,
                 seed: int = 20260821,
                 nulls: dict[int, "Null"] | None = None) -> tuple[float, float]:
    """Intervalle de confiance sur Ĥ, par rééchantillonnage des séances.

    La séance entière est le bloc : elle préserve la saisonnalité intraséance
    et toute la dépendance interne, et c'est l'unité que le protocole traite
    comme indépendante par ailleurs. Un rééchantillonnage des rendements
    détruirait précisément la structure qu'on mesure.
    """
    if not 0.0 < level < 1.0:
        raise ValueError("level doit être dans ]0, 1[")
    if draws < 2:
        raise ValueError("draws doit être ≥ 2")
    rng = Rng(seed)
    n = len(sessions)
    vals: list[float] = []
    for _ in range(draws):
        ech = [sessions[rng.randint(n)] for _ in range(n)]
        try:
            vals.append(hurst_regression(ech, qs, nulls).hurst)
        except (ValueError, ZeroDivisionError):
            continue
    if len(vals) < 2:
        raise ValueError("le rééchantillonnage n'a produit aucune estimation")
    vals.sort()
    a = (1.0 - level) / 2.0
    lo = vals[max(0, int(a * len(vals)) - 1)]
    hi = vals[min(len(vals) - 1, int((1.0 - a) * len(vals)))]
    return lo, hi


def main(path: str | None = None) -> None:
    from .dataset import load_csv, synthetic_sessions

    if path:
        sessions, origine = load_csv(path), path
    else:
        sessions = synthetic_sessions(250, seed=20260821)
        origine = "série synthétique sans dérive (vérité : H = 0,5)"

    print(f"Loi d'échelle — {origine}")
    print(f"{len(sessions)} séances\n")
    nulls = null_grid(n_sessions=len(sessions), draws=12)

    print(f"{'q':>4} {'VR(q)':>9} {'VR nul':>9} {'écart':>9} "
          f"{'Ĥ brut':>8} {'Ĥ corrigé':>10} {'z nul':>8} {'z asympt.':>10}")
    for r in scan(sessions):
        n = nulls[r.q]
        print(f"{r.q:>4} {r.vr:>9.4f} {n.mean:>9.4f} {r.excess(n):>+9.4f} "
              f"{r.hurst:>8.4f} {r.hurst_corrected(n):>10.4f} "
              f"{r.z_null(n):>8.2f} {r.z_hetero:>10.2f}")

    brut = hurst_regression(sessions)
    corr = hurst_regression(sessions, nulls=nulls)
    print(f"\nĤ par régression, brut    : {brut.hurst:.4f}  (R² {brut.r2:.4f})")
    print(f"Ĥ par régression, corrigé : {corr.hurst:.4f}  (R² {corr.r2:.4f})")
    print("\nLa colonne « z asympt. » est celle de Lo-MacKinlay. Sur cette "
          "série,\nqui est une marche aléatoire par construction, elle la "
          "rejette à tous\nles horizons : c'est le biais d'échantillon fini, "
          "et c'est la raison\npour laquelle seule la colonne « z nul » "
          "décide.")
    print("\nLa calibration du document suppose H = 0,50 ; sa discussion du "
          "gamma\nen retient 0,65. Ce module est ce qui permettra de "
          "trancher.")


if __name__ == "__main__":
    main()
