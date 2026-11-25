"""Famille B — le bandit : apprendre en gagnant, contre le hasard (Open Bandit Dataset).

Pendant sept jours, ZOZOTOWN a tiré au sort quelle politique choisissait les
trois articles montrés à chaque visite : l'**échantillonnage de Thompson**
(chaque article a une estimation de son taux de clic, avec son incertitude ; on
tire une valeur plausible par article et l'on montre les meilleurs, si bien que
les articles qui marchent reviennent souvent et les autres restent essayés),
ou le **hasard uniforme**. Le tirage au sort entre les deux politiques fait de
l'écart de clics un effet causal. L'agence fait la même chose quand elle choisit
quel contenu proposer à quel fan : pousser ce qui marche **en continuant
d'essayer le reste**, plutôt que de tout tourner au hasard, ou de ne plus jamais
essayer.
"""

from __future__ import annotations

import math
from functools import lru_cache

from . import donnees4, stats, stress
from . import registre4 as R4
from .resultat import Resultat, entier

IDS = {"all": "B01", "men": "B02", "women": "B03"}
NOM = {"all": "tous les articles", "men": "rayon hommes", "women": "rayon femmes"}
MILIEU = "2019-11-27T12:00:00"  # la moitié de la semaine du test


def _ts(r: dict) -> str:
    return r["horodatage"].replace(" ", "T")


@lru_cache(maxsize=None)
def lignes(campagne: str) -> tuple[dict, ...]:
    return tuple(r for r in donnees4.obp() if r["campagne"] == campagne)


def _compte(rows, filtre=lambda r: True) -> tuple[int, int, int, int]:
    nb = cb = nr = cr = 0
    for r in rows:
        if not filtre(r):
            continue
        if r["politique"] == "b":
            nb += 1
            cb += r["clic"]
        else:
            nr += 1
            cr += r["clic"]
    return nb, cb, nr, cr


def _ecart(nb, cb, nr, cr) -> tuple[float, float]:
    pb, pr = cb / nb, cr / nr
    se = math.sqrt(pb * (1 - pb) / nb + pr * (1 - pr) / nr)
    return (pb - pr) * 100, se * 100


def _mh(comptes: list[tuple[int, int, int, int]]) -> tuple[float, float]:
    """Écart de Mantel-Haenszel (points) et son écart-type, sur des strates (campagnes)."""
    num = den = var = 0.0
    for nb, cb, nr, cr in comptes:
        if not nb or not nr:
            continue
        w = nb * nr / (nb + nr)
        d, se = _ecart(nb, cb, nr, cr)
        num += w * d
        den += w
        var += w * w * se * se
    return num / den, math.sqrt(var) / den


def _permutation(comptes: list[tuple[int, int, int, int]], tirages: int, nom: str) -> float:
    """p bilatérale : les étiquettes de politique mélangées dans chaque strate (tirage hypergéométrique)."""
    obs, _ = _mh(comptes)
    alea = stats.rng(f"b-perm-{nom}")
    k = 0
    for _ in range(tirages):
        sim = []
        for nb, cb, nr, cr in comptes:
            N, C = nb + nr, cb + cr
            dans_b = sum(1 for pos in alea.sample(range(N), C) if pos < nb)
            sim.append((nb, dans_b, nr, C - dans_b))
        k += abs(_mh(sim)[0]) >= abs(obs) - 1e-12
    return (k + 1) / (tirages + 1)


def _jours(rows) -> list[str]:
    return sorted({_ts(r)[:10] for r in rows})


def _strates(campagnes, filtre=lambda r: True):
    return [_compte(lignes(c), filtre) for c in campagnes]


@lru_cache(maxsize=None)
def mesure(campagnes: tuple[str, ...]) -> dict:
    comptes = _strates(campagnes)
    d, se = _mh(comptes)
    p = _permutation(comptes, R4.TIRAGES, "-".join(campagnes))
    # Spécification : position (1, 2, 3) × moitié de semaine.
    spec, noms = [], []
    for pos in (1, 2, 3):
        for moitie in (0, 1):
            f = (lambda r, pos=pos, moitie=moitie: r["position"] == pos and ((_ts(r) >= MILIEU) == bool(moitie)))
            ds, ses = _mh(_strates(campagnes, f))
            spec.append((ds, stats.p_bilateral(ds / ses) if ses > 0 else 1.0))
            noms.append((pos, moitie))
    # Temps : l'écart jour par jour (sept jours), et son Sharpe dégonflé.
    jours = _jours(lignes(campagnes[0]))
    par_jour = []
    for j in jours:
        dj, _ = _mh(_strates(campagnes, lambda r, j=j: _ts(r).startswith(j)))
        par_jour.append(dj)
    # Placebo : le tirage au sort a-t-il mélangé les mêmes clients ? (empreinte u0, khi-deux)
    placebo = _equilibre(campagnes)
    n = sum(a + c for a, _, c, _ in comptes)
    taux = [(cb / nb * 100, cr / nr * 100) for nb, cb, nr, cr in comptes]
    return {"d": d, "se": se, "p": p, "n": n, "spec": spec, "spec_noms": noms, "jours": jours,
            "par_jour": par_jour, "dsr": stress.dsr(par_jour, 1), "placebo": placebo, "taux": taux,
            "comptes": comptes}


def _equilibre(campagnes) -> tuple[float, float]:
    """Khi-deux d'équilibre de l'empreinte u0 entre les deux bras (catégories d'au moins 5 attendus)."""
    stat = 0.0
    ddl = 0
    for c in campagnes:
        cnt: dict[int, list[int]] = {}
        for r in lignes(c):
            e = cnt.setdefault(r["u0"], [0, 0])
            e[r["politique"] == "b"] += 1
        nr = sum(v[0] for v in cnt.values())
        nb = sum(v[1] for v in cnt.values())
        reste = [0, 0]
        cats = []
        for v in cnt.values():
            tot = v[0] + v[1]
            if min(tot * nr, tot * nb) / (nr + nb) >= 5:
                cats.append(v)
            else:
                reste[0] += v[0]
                reste[1] += v[1]
        if sum(reste):
            cats.append(reste)
        for v in cats:
            tot = v[0] + v[1]
            er, eb = tot * nr / (nr + nb), tot * nb / (nr + nb)
            stat += (v[0] - er) ** 2 / er + (v[1] - eb) ** 2 / eb
        ddl += len(cats) - 1
    return stat, _khi2_sup(stat, ddl)


def _khi2_sup(x: float, k: int) -> float:
    """P(χ²_k ≥ x), par l'approximation de Wilson-Hilferty (assez juste pour k ≥ 3)."""
    if k <= 0:
        return 1.0
    z = ((x / k) ** (1 / 3) - (1 - 2 / (9 * k))) / math.sqrt(2 / (9 * k))
    return 1 - stats.Phi(z)


def _resultat(rid: str, campagnes: tuple[str, ...]) -> Resultat:
    m = mesure(campagnes)
    if len(campagnes) == 1:
        (tb, tr), = m["taux"]
        lecture = (f"{NOM[campagnes[0]]} : {tb:.2f} % de clics avec Thompson, {tr:.2f} % au hasard "
                   f"({entier(m['n'])} impressions)").replace(".", ",")
    else:
        lecture = (f"les trois campagnes ensemble : {m['d']:+.3f} point de clic pour Thompson "
                   f"({entier(m['n'])} impressions)").replace(".", ",")
    return Resultat(id=rid, effet=m["d"], ic=(m["d"] - 1.96 * m["se"], m["d"] + 1.96 * m["se"]), p=m["p"],
                    n=m["n"], unite="pt", lecture=lecture,
                    methode="politiques tirées au sort ; permutation des étiquettes dans chaque campagne")


@lru_cache(maxsize=1)
def resultats() -> dict[str, Resultat]:
    out = {rid: _resultat(rid, (c,)) for c, rid in IDS.items()}
    out["B04"] = _resultat("B04", R4.CAMPAGNES)
    return out


def batteries() -> dict[str, dict]:
    out = {rid: mesure((c,)) for c, rid in IDS.items()}
    out["B04"] = mesure(R4.CAMPAGNES)
    return out


def main() -> None:
    for i, r in resultats().items():
        m = batteries()[i]
        print(i, f"{r.effet:+.3f} pt [{r.ic[0]:+.3f}, {r.ic[1]:+.3f}] p={r.p:.3f}", r.lecture)
        print("    jours", [round(x, 2) for x in m["par_jour"]], "dsr", round(m["dsr"]["dsr"], 3),
              "placebo p", round(m["placebo"][1], 3), "spec", [round(a, 2) for a, _ in m["spec"]])


if __name__ == "__main__":
    main()
