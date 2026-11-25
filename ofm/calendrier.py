"""Le calendrier — un contrôle positif avant toute lecture de date.

Une méthode qui cherche des effets de calendrier dans les revenus d'une agence
doit d'abord montrer qu'elle voit un effet **connu**. Le plus propre est celui
des naissances américaines : les déclenchements et césariennes programmés
évitent le 13 du mois. La loi nulle n'est pas « un jour moyen » — le jour de
la semaine pèse beaucoup plus que la date — mais **le même jour de la semaine
une semaine avant et une semaine après** : le 6 et le 20 encadrent le 13 et
tombent le même jour que lui. Les mois où l'un des trois est un jour férié
mobile sont retirés, faute de quoi la méthode lirait le férié.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from functools import lru_cache

from . import donnees, stats
from .resultat import Resultat


def _nieme_lundi(an: int, mois: int, rang: int) -> date:
    d = date(an, mois, 1)
    d += timedelta(days=(0 - d.weekday()) % 7)
    return d + timedelta(weeks=rang - 1)


def feries_mobiles(an: int) -> set[date]:
    return {_nieme_lundi(an, 1, 3), _nieme_lundi(an, 2, 3), _nieme_lundi(an, 9, 1),
            _nieme_lundi(an, 10, 2)}


@lru_cache(maxsize=1)
def jours() -> dict[date, int]:
    return {date(a, m, j): n for a, m, j, _, n in donnees.naissances()}


@lru_cache(maxsize=1)
def ecarts_13() -> tuple[tuple[date, float], ...]:
    """Écart relatif du 13 à la moyenne du 6 et du 20, mois par mois."""
    jj = jours()
    out = []
    for a in range(2000, 2015):
        fer = feries_mobiles(a)
        for m in range(1, 13):
            d6, d13, d20 = date(a, m, 6), date(a, m, 13), date(a, m, 20)
            if fer & {d6, d13, d20}:
                continue
            ref = (jj[d6] + jj[d20]) / 2
            out.append((d13, jj[d13] / ref - 1))
    return tuple(out)


@lru_cache(maxsize=1)
def resultats() -> dict[str, Resultat]:
    e = [v for _, v in ecarts_13()]
    m, se = stats.moyenne(e), math.sqrt(stats.variance(e) / len(e))
    ven = [v for d, v in ecarts_13() if d.weekday() == 4]
    return {"T01": Resultat(
        id="T01", effet=m * 100, ic=((m - 1.96 * se) * 100, (m + 1.96 * se) * 100),
        p=stats.p_bilateral(m / se), n=len(e), unite="%",
        lecture=(f"{m * 100:+.2f} % de naissances le 13 contre le 6 et le 20 du même mois "
                 f"({len(e)} mois) ; {stats.moyenne(ven) * 100:+.2f} % un vendredi 13 "
                 f"({len(ven)} cas)").replace(".", ","),
        methode="écart apparié au même jour de la semaine, féries mobiles retirés",
        extra={"vendredi": stats.moyenne(ven), "n_vendredi": len(ven)},
    )}


@lru_cache(maxsize=1)
def profil() -> tuple[tuple[int, float, float, int], ...]:
    """Pour chaque date 1–31 : écart moyen au même jour de la semaine ±7 jours."""
    jj = jours()
    par: dict = {}
    for d, n in jj.items():
        a, b = d - timedelta(days=7), d + timedelta(days=7)
        if a in jj and b in jj:
            par.setdefault(d.day, []).append(n / ((jj[a] + jj[b]) / 2) - 1)
    out = []
    for k in range(1, 32):
        v = par[k]
        out.append((k, stats.moyenne(v), 1.96 * math.sqrt(stats.variance(v) / len(v)), len(v)))
    return tuple(out)


if __name__ == "__main__":
    print(resultats()["T01"].lecture)
    for k, m, h, n in profil():
        print(k, f"{m * 100:+.2f} ± {h * 100:.2f}", n)
