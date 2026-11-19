"""Dire oui — le speed dating de Columbia (Fisman et al., 2006).

8 378 rencontres de quatre minutes entre 551 étudiants, chacune suivie d'une
décision écrite — oui ou non — et de notes (attrait, plaisir, sincérité,
probabilité perçue d'un oui en retour). L'ordre des rencontres d'une soirée
suit la rotation des tables, ce qui en fait une expérience naturelle de
**séquence** : le partenaire qui précède n'est pas choisi.

Les hypothèses portent sur les **décisions d'hommes** (le registre le dit) :
le public d'une page d'abonnement est masculin et c'est sa décision qui paie.

L'attrait d'une personne est mesuré par la moyenne des notes **des autres**
(le décideur courant est exclu) : sinon la note et la décision viendraient de
la même tête, et l'on mesurerait une cohérence, pas un effet. Les effets
fixes par décideur se font par centrage, les écarts-types par grappe.
"""

from __future__ import annotations

import math
from functools import lru_cache

from . import donnees, stats
from .resultat import Resultat, entier


@lru_cache(maxsize=1)
def lignes() -> tuple[dict, ...]:
    return tuple(r for r in donnees.speed() if r["pid"] is not None and r["dec"] is not None)


@lru_cache(maxsize=1)
def _notes_recues() -> dict:
    """{personne: {évaluateur: note d'attrait}} — les notes que chacun a reçues."""
    out: dict = {}
    for r in lignes():
        if r["attr"] is not None:
            out.setdefault(int(r["pid"]), {})[int(r["iid"])] = r["attr"]
    return out


def attrait_autres(cible: int, sauf: int) -> tuple[float, float, int] | None:
    """Moyenne, écart-type et nombre des notes reçues par `cible`, sans `sauf`."""
    notes = [v for k, v in _notes_recues().get(cible, {}).items() if k != sauf]
    if len(notes) < 2:
        return None
    m = sum(notes) / len(notes)
    s = math.sqrt(sum((v - m) ** 2 for v in notes) / (len(notes) - 1))
    return m, s, len(notes)


def _centrer(rows: list[dict], cles: list[str], groupe: str) -> list[dict]:
    par: dict = {}
    for r in rows:
        par.setdefault(r[groupe], []).append(r)
    out = []
    for g, rs in par.items():
        if len(rs) < 2:
            continue
        moy = {k: sum(r[k] for r in rs) / len(rs) for k in cles}
        for r in rs:
            out.append({**r, **{k + "_c": r[k] - moy[k] for k in cles}})
    return out


def _fit_centre(rows: list[dict], y: str, xs: list[str], groupe: str) -> stats.Ajustement:
    c = _centrer(rows, [y, *xs], groupe)
    X = [[r[x + "_c"] for x in xs] for r in c]
    return stats.mco(X, [r[y + "_c"] for r in c], xs, grappes=[r[groupe] for r in c])


@lru_cache(maxsize=1)
def sequences() -> tuple[dict, ...]:
    """Décisions d'hommes, avec l'attrait de la partenaire courante et précédente."""
    par: dict = {}
    for r in lignes():
        if r["gender"] == 1.0:
            par.setdefault(int(r["iid"]), []).append(r)
    out = []
    for i, rs in par.items():
        rs = sorted(rs, key=lambda r: r["order"])
        rang = {int(r["order"]): r for r in rs}
        nmax = max(int(r["round"]) for r in rs)
        for r in rs:
            cur = attrait_autres(int(r["pid"]), i)
            if cur is None:
                continue
            k = int(r["order"])
            prev = rang.get(k - 1)
            pa = attrait_autres(int(prev["pid"]), i) if prev else None
            out.append({
                "i": i, "y": r["dec"], "ordre": k, "n": nmax,
                "frac": (k - 1) / (nmax - 1) if nmax > 1 else 0.0,
                "cur": cur[0], "prev": pa[0] if pa else None,
                "prob": r["prob"], "attr": r["attr"], "fun": r["fun"],
                "pid": int(r["pid"]),
            })
    return tuple(out)


def _res(rid, fit, nom, echelle, unite, lecture, methode, n) -> Resultat:
    lo, hi = fit.ic(nom)
    return Resultat(id=rid, effet=fit.b(nom) * echelle, ic=(lo * echelle, hi * echelle),
                    p=fit.p(nom), n=n, unite=unite, lecture=lecture, methode=methode)


@lru_cache(maxsize=1)
def resultats() -> dict[str, Resultat]:
    out = {}
    seq = sequences()
    base = sum(s["y"] for s in seq) / len(seq)

    # S01 : contraste avec la partenaire précédente.
    rows = [s for s in seq if s["prev"] is not None]
    fit = _fit_centre(rows, "y", ["cur", "prev"], "i")
    out["S01"] = _res("S01", fit, "prev", 100, "pt par point",
                      (f"un point d'attrait de plus chez la précédente : {fit.b('prev') * 100:+.2f} pt "
                       f"de oui ; un point chez la courante : {fit.b('cur') * 100:+.2f} pt").replace(".", ","),
                      "effets fixes par décideur, grappes par décideur", len(rows))
    out["S01"].extra = {"cur": fit.b("cur"), "base": base, "grappes": fit.groupes}

    # S02 : rang dans la soirée (de la première à la dernière rencontre).
    fit = _fit_centre(list(seq), "y", ["frac", "cur"], "i")
    out["S02"] = _res("S02", fit, "frac", 100, "pt",
                      (f"de la première à la dernière rencontre : {fit.b('frac') * 100:+.2f} pt de oui, "
                       f"à attrait égal").replace(".", ","),
                      "effets fixes par décideur, grappes par décideur", len(seq))

    # S07 : la première rencontre contre celles du milieu.
    rows = [{**s, "prem": 1.0 if s["ordre"] == 1 else 0.0} for s in seq if s["ordre"] < s["n"]]
    fit = _fit_centre(rows, "y", ["prem", "cur"], "i")
    out["S07"] = _res("S07", fit, "prem", 100, "pt",
                      f"première rencontre : {fit.b('prem') * 100:+.2f} pt de oui contre le milieu".replace(".", ","),
                      "effets fixes par décideur, grappes par décideur", len(rows))

    # S06 : croire être aimé.
    rows = [s for s in seq if None not in (s["prob"], s["attr"], s["fun"])]
    fit = _fit_centre(rows, "y", ["prob", "attr", "fun"], "i")
    out["S06"] = _res("S06", fit, "prob", 100, "pt par point",
                      (f"un point de probabilité perçue : {fit.b('prob') * 100:+.2f} pt de oui ; "
                       f"un point d'attrait : {fit.b('attr') * 100:+.2f} pt").replace(".", ","),
                      "effets fixes par décideur, grappes par décideur", len(rows))

    # S03 : le désir non sélectif de la femme, et le oui qu'elle reçoit des hommes.
    par: dict = {}
    for r in lignes():
        if r["gender"] == 0.0:
            par.setdefault(int(r["iid"]), []).append(r)
    rows = []
    for i, rs in par.items():
        if len(rs) < 3:
            continue
        tot = sum(r["dec"] for r in rs)
        for r in rs:
            if r["dec_o"] is None:
                continue
            a = attrait_autres(i, int(r["pid"]))
            if a is None:
                continue
            rows.append({"i": i, "y": r["dec_o"], "nonsel": (tot - r["dec"]) / (len(rs) - 1),
                         "att": a[0]})
    X = [[1.0, r["nonsel"], r["att"]] for r in rows]
    fit = stats.mco(X, [r["y"] for r in rows], ["c", "nonsel", "att"],
                    grappes=[r["i"] for r in rows])
    out["S03"] = _res("S03", fit, "nonsel", 10, "pt par 10 pt",
                      (f"dix points de oui donnés en plus ailleurs : {fit.b('nonsel') * 10:+.2f} pt "
                       f"de oui reçu, à attrait égal").replace(".", ","),
                      "moindres carrés, grappes par personne", len(rows))

    # S04 : réciprocité dyadique du goût relatif.
    goût: dict = {}
    for r in lignes():
        if r["like"] is not None:
            goût.setdefault(int(r["iid"]), {})[int(r["pid"])] = r["like"]
    moy = {i: sum(v.values()) / len(v) for i, v in goût.items() if len(v) >= 3}
    paires = []
    for i, v in goût.items():
        for j, l_ij in v.items():
            if i < j and i in moy and j in moy and i in goût.get(j, {}):
                paires.append((l_ij - moy[i], goût[j][i] - moy[j], i, j))
    X = [[1.0, a] for a, _, _, _ in paires]
    fit = stats.mco(X, [b for _, b, _, _ in paires], ["c", "rel"])
    r = stats.correlation([a for a, *_ in paires], [b for _, b, *_ in paires])
    out["S04"] = _res("S04", fit, "rel", 1, "pente",
                      (f"un point de goût relatif donné appelle {fit.b('rel'):+.3f} point rendu "
                       f"(corrélation {r:+.3f}, {entier(len(paires))} paires)").replace(".", ","),
                      "moindres carrés sur les paires, robuste", len(paires))
    out["S04"].extra = {"r": r}

    # S05 : dispersion des goûts, mesurée chez les autres hommes.
    rows = polarisation_lignes()
    X = [[1.0, r["m"], r["s"], r["m"] * r["s"]] for r in rows]
    fit = stats.mco(X, [r["y"] for r in rows], ["c", "m", "s", "ms"],
                    grappes=[r["cible"] for r in rows])
    ms = [r["m"] for r in rows]
    bas, haut = stats.quantile(ms, 0.1), stats.quantile(ms, 0.9)
    pente = lambda m: (fit.b("s") + fit.b("ms") * m) * 100
    out["S05"] = _res("S05", fit, "ms", 100, "pt par point²",
                      (f"un point d'écart-type des notes vaut {pente(bas):+.1f} pt de oui pour une "
                       f"moyenne basse ({bas + polarisation_centre()[0]:.1f}/10) et {pente(haut):+.1f} pt "
                       f"pour une moyenne haute ({haut + polarisation_centre()[0]:.1f}/10)").replace(".", ","),
                      "moindres carrés, notes des autres hommes, grappes par femme", len(rows))
    out["S05"].extra = {"b_s": fit.b("s"), "b_m": fit.b("m"), "b_ms": fit.b("ms"),
                        "c": fit.b("c"), "bas": bas, "haut": haut}
    return {k: out[k] for k in sorted(out)}


@lru_cache(maxsize=1)
def polarisation_centre() -> tuple[float, float]:
    rows = _polarisation_brut()
    return (sum(r["m"] for r in rows) / len(rows), sum(r["s"] for r in rows) / len(rows))


@lru_cache(maxsize=1)
def _polarisation_brut() -> tuple[dict, ...]:
    out = []
    for r in lignes():
        if r["gender"] != 1.0:
            continue
        a = attrait_autres(int(r["pid"]), int(r["iid"]))
        if a is None or a[2] < 5:
            continue
        out.append({"y": r["dec"], "m": a[0], "s": a[1], "cible": int(r["pid"])})
    return tuple(out)


@lru_cache(maxsize=1)
def polarisation_lignes() -> tuple[dict, ...]:
    mc, sc = polarisation_centre()
    return tuple({**r, "m": r["m"] - mc, "s": r["s"] - sc} for r in _polarisation_brut())


def surface_polarisation(nm: int = 7, ns: int = 7) -> tuple[list[list[float]], list[float], list[float]]:
    """Taux de oui prédit par le modèle S05 sur une grille moyenne × écart-type."""
    ex = resultats()["S05"].extra
    mc, sc = polarisation_centre()
    rows = _polarisation_brut()
    m_lo, m_hi = stats.quantile([r["m"] for r in rows], .05), stats.quantile([r["m"] for r in rows], .95)
    s_lo, s_hi = stats.quantile([r["s"] for r in rows], .05), stats.quantile([r["s"] for r in rows], .95)
    ms = [m_hi - k * (m_hi - m_lo) / (nm - 1) for k in range(nm)]
    ss = [s_hi - k * (s_hi - s_lo) / (ns - 1) for k in range(ns)]
    z = [[ex["c"] + ex["b_m"] * (m - mc) + ex["b_s"] * (s - sc) + ex["b_ms"] * (m - mc) * (s - sc)
          for s in ss] for m in ms]
    return z, ms, ss


@lru_cache(maxsize=1)
def contraste_grille(k: int = 4) -> tuple[list[list[float]], list[float], list[float]]:
    """Taux de oui brut par quartile d'attrait courant (lignes) et précédent (colonnes)."""
    rows = [s for s in sequences() if s["prev"] is not None]
    qc = [stats.quantile([r["cur"] for r in rows], (i + 1) / k) for i in range(k - 1)]
    qp = [stats.quantile([r["prev"] for r in rows], (i + 1) / k) for i in range(k - 1)]

    def rang(v, b):
        return sum(1 for x in b if v > x)

    s = [[0.0] * k for _ in range(k)]
    n = [[0] * k for _ in range(k)]
    for r in rows:
        a, b = rang(r["cur"], qc), rang(r["prev"], qp)
        s[a][b] += r["y"]
        n[a][b] += 1
    return [[s[a][b] / n[a][b] for b in range(k)] for a in range(k)], qc, qp


def oui_par_rang(maxi: int = 20) -> list[tuple[int, float, int]]:
    out = []
    for k in range(1, maxi + 1):
        ys = [s["y"] for s in sequences() if s["ordre"] == k]
        if len(ys) >= 40:
            out.append((k, sum(ys) / len(ys), len(ys)))
    return out


def main() -> None:
    from .registre import par_id
    reg = par_id()
    for i, r in resultats().items():
        print(f"{i} {reg[i].enonce[:58]:58s} {r.effet:+7.3f} {r.unite} "
              f"[{r.ic[0]:+.3f}, {r.ic[1]:+.3f}] p={r.p:.4f} n={r.n}  {r.lecture}")
    print(contraste_grille()[0])


if __name__ == "__main__":
    main()
