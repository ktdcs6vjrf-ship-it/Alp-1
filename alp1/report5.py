"""Tables des deux instruments de mesure : loi d'échelle et remplissage du stop.

Le document affirmait que le Test 1 mesure l'exposant d'échelle par ratio de
variance, et `scan_session` documentait son propre optimisme sur le
remplissage du stop sans que rien ne le chiffre. Les deux manques sont comblés
par `alp1.varratio` et par `alp1.measure.bounds` ; ce module en tire les tables
et les valeurs du document.

Les deux séries de nombres portent sur une **série synthétique sans dérive**,
et c'est délibéré : ce ne sont pas des mesures du marché mais des mesures des
instruments de mesure. Ce qu'elles établissent — que la statistique du manuel
rejette la marche aléatoire sur une marche aléatoire, et que l'hypothèse de
remplissage pèse plus lourd que la friction — se lit sans aucune donnée de
prix, et devait être su avant d'en ouvrir une.
"""

from __future__ import annotations

from .dataset import synthetic_sessions
from .measure import bounds
from .report import Table, num
from .report3 import year as _plain


def seed_label(x: int) -> str:
    """Une graine est un identifiant : elle s'écrit sans séparateur."""
    return _plain(x)
from .varratio import Q_GRID, hurst_regression, null_grid, scan

#: Longueur de la série de contrôle, en séances. Le document cite ces nombres ;
#: ils doivent donc être reproductibles à l'identique, graine comprise.
N_SESSIONS = 250
SEED = 20260821

#: Graines du balayage de l'encadrement. Trois suffisent à montrer que la
#: largeur de la bande ne dépend pas du tirage, alors que le renversement de
#: signe en dépend.
SEEDS = (20260821, 11, 4242)

#: Tirages de la loi nulle de l'estimateur. Mémorisée par `null_grid`, elle
#: n'est simulée qu'une fois par exécution.
NULL_DRAWS = 8


def _control():
    return synthetic_sessions(N_SESSIONS, seed=SEED)


def table_varratio() -> Table:
    sessions = _control()
    nulls = null_grid(n_sessions=N_SESSIONS, draws=NULL_DRAWS)
    rows = []
    for r in scan(sessions):
        n = nulls[r.q]
        rows.append([
            num(r.q, 0),
            num(r.vr, 4),
            num(n.mean, 4),
            num(r.hurst, 4),
            num(r.hurst_corrected(n), 4),
            num(r.z_hetero, 2),
            num(r.z_null(n), 2),
        ])
    return Table(
        "varratio",
        "Ratio de variance mesuré sur une série sans dérive, et ce que "
        "l'estimateur en dit — brut, puis rapporté à sa propre loi nulle.",
        ["q (min)", "VR(q)", "VR sous marche aléatoire", "Ĥ brut",
         "Ĥ corrigé", "z asymptotique", "z contre la nulle"],
        rows,
        wide=True,
        note="La série est une marche aléatoire par construction : la seule "
             "réponse juste est Ĥ = 0,50 et un z qui ne rejette rien. La "
             "colonne « z asymptotique » est celle de Lo et MacKinlay ; elle "
             "rejette la marche aléatoire à tous les horizons. C'est le biais "
             "d'échantillon fini de l'estimateur sur des séances de 390 "
             "minutes, non une propriété du prix. Seule la dernière colonne "
             "décide.")


def table_bounds() -> Table:
    rows = []
    for seed in SEEDS:
        b = bounds(synthetic_sessions(N_SESSIONS, seed=seed))
        renverse = b.optimistic.mean_net > 0.0 > b.worst.mean_net
        rows.append([
            seed_label(seed),
            num(b.optimistic.mean_net, 4),
            num(b.worst.mean_net, 4),
            num(b.spread_points, 4),
            num(b.optimistic.friction_used, 4),
            "oui" if renverse else "non",
        ])
    return Table(
        "fillbounds",
        "La même mesure sous les deux remplissages du stop, sur trois tirages "
        "d'une série sans dérive.",
        ["Tirage", "Au stop (pt)", "À l'extrême (pt)", "Écart (pt)",
         "Friction (pt)", "Signe renversé"],
        rows,
        wide=True,
        note="Deux lectures, de statut différent. L'écart entre les deux "
             "remplissages ne dépend pas du tirage et dépasse la friction à "
             "chaque fois : l'hypothèse d'exécution pèse plus lourd que la "
             "grandeur que la mesure cherche à franchir. Le renversement de "
             "signe, lui, dépend du tirage — mais il survient dès que "
             "l'espérance vraie tombe dans la bande, et la bande est plus "
             "large que la friction.")


TABLES = [table_varratio, table_bounds]


def all_tables() -> dict[str, Table]:
    return {fn().key: fn() for fn in TABLES}


def values() -> dict[str, str]:
    sessions = _control()
    nulls = null_grid(n_sessions=N_SESSIONS, draws=NULL_DRAWS)
    res = scan(sessions)
    brut = hurst_regression(sessions)
    corr = hurst_regression(sessions, nulls=nulls)
    z_asym = [abs(r.z_hetero) for r in res]
    z_nul = [abs(r.z_null(nulls[r.q])) for r in res]

    bs = [bounds(synthetic_sessions(N_SESSIONS, seed=s)) for s in SEEDS]
    ecarts = [b.spread_points for b in bs]
    ref = bs[0]

    return {
        # --- loi d'échelle mesurée ---
        "vr_n": num(N_SESSIONS, 0),
        "vr_qmin": num(min(Q_GRID), 0),
        "vr_qmax": num(max(Q_GRID), 0),
        "vr_h_brut": num(brut.hurst, 4),
        "vr_h_corr": num(corr.hurst, 4),
        "vr_z_asym_lo": num(min(z_asym), 2),
        "vr_z_asym_hi": num(max(z_asym), 2),
        "vr_z_nul_hi": num(max(z_nul), 2),
        "vr_null_hi": num(max(nulls[q].mean for q in Q_GRID), 4),

        # --- encadrement du remplissage ---
        "fill_opt": num(ref.optimistic.mean_net, 4),
        "fill_bad": num(ref.worst.mean_net, 4),
        "fill_spread": num(ref.spread_points, 4),
        "fill_spread_pct": num(ref.spread_fraction * 100, 0),
        "fill_friction": num(ref.optimistic.friction_used, 4),
        "fill_spread_lo": num(min(ecarts), 2),
        "fill_spread_hi": num(max(ecarts), 2),
        "fill_flips": num(sum(b.optimistic.mean_net > 0 > b.worst.mean_net
                              for b in bs), 0),
        "fill_seeds": num(len(SEEDS), 0),
    }


def main() -> None:
    for i, fn in enumerate(TABLES, start=1):
        t = fn()
        print(f"\n### Table {i} — {t.caption}\n")
        print(t.to_text())
    print("\n\nValeurs\n")
    for k, v in sorted(values().items()):
        print(f"  {k:20} {v}")


if __name__ == "__main__":
    main()
