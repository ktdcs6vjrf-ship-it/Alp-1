"""Les leviers — cinq gestes tirés au sort sur le terrain (famille L du cahier nº 3).

Chaque expérience a été menée par d'autres chercheurs : le geste (un bonus, une
annonce, un format, une carte, une posture) a été **tiré au sort**, si bien que
l'écart entre les groupes mesure le geste et rien d'autre. Le cahier refait le
calcul à partir des données publiées, avec la loi nulle qui respecte le tirage :
on mélange l'étiquette du geste là où le tirage l'a mélangée (dans le village,
dans le hameau, dans le service), jamais au-delà.

Le tirage de Cai, de Janvry et Sadoulet porte sur des hameaux entiers : le
choix par défaut se mélange donc par hameau, pas par foyer (sinon la loi nulle
serait trop étroite et le test trop facile).
"""

from __future__ import annotations

import math
from functools import lru_cache

from alp1.figterm import _num

from . import donnees3, stats
from .registre3 import BONUS_GRAND, BONUS_PETIT
from .resultat import Resultat, entier

TIRAGES = 4999


def _pct(v: float, nd: int = 1) -> str:
    return f"{_num(v * 100, nd)} %"


def _s(v: float, nd: int = 1) -> str:
    """Un nombre signé à la française, avec le vrai signe moins."""
    return ("+" if v >= 0 else "−") + _num(abs(v), nd)


def _perm_p(obs: float, nul: list[float]) -> float:
    k = sum(1 for v in nul if abs(v) >= abs(obs) - 1e-12)
    return (k + 1) / (len(nul) + 1)


def _pente(x: list[float], y: list[float]) -> tuple[float, float]:
    """Pente des moindres carrés et son écart-type robuste (HC1)."""
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    b = sum((a - mx) * (c - my) for a, c in zip(x, y)) / sxx
    e = [c - my - b * (a - mx) for a, c in zip(x, y)]
    v = sum(((a - mx) * r) ** 2 for a, r in zip(x, e)) / sxx ** 2 * n / (n - 2)
    return b, math.sqrt(v)


def _perm_pente(x: list[float], y: list[float], strates: list, nom: str, tirages: int = TIRAGES) -> list[float]:
    """Loi nulle d'une pente : les valeurs de x mélangées à l'intérieur de chaque strate."""
    alea = stats.rng(nom)
    blocs: dict = {}
    for i, s in enumerate(strates):
        blocs.setdefault(s, []).append(i)
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    yc = [c - my for c in y]
    groupes = [([x[i] for i in idx], [yc[i] for i in idx]) for idx in blocs.values()]
    out = []
    for _ in range(tirages):
        s = 0.0
        for xs, ys in groupes:
            alea.shuffle(xs)
            s += sum(a * b for a, b in zip(xs, ys))
        out.append(s / sxx)
    return out


def _proportions(id_: str, a: list[int], b: list[int], nom: str, quoi: str, methode: str,
                 extra: dict | None = None) -> Resultat:
    """A contre B (référence), permutation simple des étiquettes."""
    y = a + b
    g = [1] * len(a) + [0] * len(b)
    obs, p, _ = stats.permutation(y, g, tirages=TIRAGES, nom=nom)
    e = stats.deux_proportions(sum(a), len(a), sum(b), len(b))
    lo, hi = e.ic()
    return Resultat(id=id_, effet=obs * 100, ic=(lo * 100, hi * 100), p=p, n=len(y), unite="pt",
                    lecture=f"{_pct(e.a)} contre {_pct(e.b)} ({quoi})", methode=methode,
                    base=e.b, relatif=e.relatif, extra={"a": e.a, "b": e.b, "na": len(a), "nb": len(b),
                                                        **(extra or {})})


# ---------------------------------------------------------------------------
# Thornton (2008) : un bonus, la distance
# ---------------------------------------------------------------------------

def _thornton() -> dict[str, Resultat]:
    T = donnees3.thornton()
    out = {}
    # L01 — un bonus quelconque contre aucun, permutation dans le village.
    y = [r["retire"] for r in T]
    g = [r["bonus"] for r in T]
    obs, p, _ = stats.permutation(y, g, strates=[r["village"] for r in T], tirages=TIRAGES, nom="L01")
    a = [r["retire"] for r in T if r["bonus"]]
    b = [r["retire"] for r in T if not r["bonus"]]
    e = stats.deux_proportions(sum(a), len(a), sum(b), len(b))
    lo, hi = e.ic()
    out["L01"] = Resultat(
        id="L01", effet=obs * 100, ic=(lo * 100, hi * 100), p=p, n=len(T), unite="pt",
        lecture=f"{_pct(e.a)} vont chercher leur résultat avec un bonus, {_pct(e.b)} sans",
        methode=f"écart de proportions ; {TIRAGES} permutations du bonus dans le village",
        base=e.b, relatif=e.relatif, extra={"a": e.a, "b": e.b, "na": len(a), "nb": len(b)})
    # L02 — la pente selon le montant, chez qui a reçu un bonus.
    B = [r for r in T if r["bonus"]]
    x, yb = [r["montant"] for r in B], [r["retire"] * 100.0 for r in B]
    pente, se = _pente(x, yb)
    nul = _perm_pente(x, yb, [r["village"] for r in B], "L02")
    out["L02"] = Resultat(
        id="L02", effet=pente, ic=(pente - 1.96 * se, pente + 1.96 * se), p=_perm_p(pente, nul), n=len(B),
        unite="pt par dollar",
        lecture=f"{_s(pente)} points par dollar de bonus en plus, chez {entier(len(B))} personnes qui en ont reçu un",
        methode=f"pente des moindres carrés (écart-type robuste) ; {TIRAGES} permutations des montants dans le village")
    # L03 — le premier pas contre tout le reste.
    def d3(rows):
        rien = [r["retire"] for r in rows if not r["bonus"]]
        petit = [r["retire"] for r in rows if r["bonus"] and r["montant"] <= BONUS_PETIT]
        grand = [r["retire"] for r in rows if r["bonus"] and r["montant"] > BONUS_GRAND]
        if not rien or not petit or not grand:
            return None
        p0, p1, p2 = sum(rien) / len(rien), sum(petit) / len(petit), sum(grand) / len(grand)
        return (p1 - p0) - (p2 - p1), p0, p1, p2, len(rien), len(petit), len(grand)

    D, p0, p1, p2, n0, n1, n2 = d3(T)
    villages: dict[int, list] = {}
    for r in T:
        villages.setdefault(r["village"], []).append(r)
    cles = sorted(villages)
    alea = stats.rng("L03")
    boot = []
    for _ in range(1999):
        tirage = [r for _ in cles for r in villages[cles[alea.randrange(len(cles))]]]
        v = d3(tirage)
        if v is not None:
            boot.append(v[0])
    k_bas, k_haut = sum(1 for v in boot if v <= 0), sum(1 for v in boot if v >= 0)
    out["L03"] = Resultat(
        id="L03", effet=D * 100, ic=(stats.quantile(boot, 0.025) * 100, stats.quantile(boot, 0.975) * 100),
        p=min(1.0, 2 * (1 + min(k_bas, k_haut)) / (len(boot) + 1)), n=n0 + n1 + n2, unite="pt",
        lecture=(f"sans bonus {_pct(p0)}, petit bonus (≤ {_num(BONUS_PETIT, 2)} $) {_pct(p1)}, grand "
                 f"(> {_num(BONUS_GRAND, 2)} $) {_pct(p2)} : le premier pas fait {_num((p1 - p0) * 100, 1)} pt, "
                 f"tout le reste {_num((p2 - p1) * 100, 1)} pt"),
        methode="différence des deux marches ; 1 999 rééchantillonnages des villages",
        extra={"p0": p0, "p1": p1, "p2": p2, "n0": n0, "n1": n1, "n2": n2})
    # L04 — la distance, tout le monde, permutation dans le village.
    x, yd = [r["distance"] for r in T], [r["retire"] * 100.0 for r in T]
    pente, se = _pente(x, yd)
    nul = _perm_pente(x, yd, [r["village"] for r in T], "L04")
    out["L04"] = Resultat(
        id="L04", effet=pente, ic=(pente - 1.96 * se, pente + 1.96 * se), p=_perm_p(pente, nul), n=len(T),
        unite="pt par km",
        lecture=f"{_s(pente)} points par kilomètre entre la maison et le centre, {entier(len(T))} personnes",
        methode=f"pente des moindres carrés (écart-type robuste) ; {TIRAGES} permutations des distances dans le village")
    return out


def dose_reponse() -> list[tuple[str, float, int]]:
    """Le retrait par tranche de bonus (pour le graphique)."""
    T = donnees3.thornton()
    tranches = (("aucun", lambda m, b: not b), ("≤ 0,25 $", lambda m, b: b and m <= 0.25),
                ("0,25–0,50 $", lambda m, b: b and 0.25 < m <= 0.5), ("0,50–1,00 $", lambda m, b: b and 0.5 < m <= 1.0),
                ("1,00–1,50 $", lambda m, b: b and 1.0 < m <= 1.5), ("1,50–2,00 $", lambda m, b: b and 1.5 < m <= 2.0),
                ("> 2,00 $", lambda m, b: b and m > 2.0))
    out = []
    for nom, test in tranches:
        rows = [r["retire"] for r in T if test(r["montant"], r["bonus"])]
        out.append((nom, sum(rows) / len(rows), len(rows)))
    return out


def grille_bonus_distance() -> tuple[list[list[float]], list[str], list[str], list[list[int]]]:
    """Retrait par (tranche de bonus × tranche de distance), pour le relief."""
    T = donnees3.thornton()
    bonus = (("aucun", lambda r: not r["bonus"]), ("petit", lambda r: r["bonus"] and r["montant"] <= BONUS_PETIT),
             ("moyen", lambda r: r["bonus"] and BONUS_PETIT < r["montant"] <= BONUS_GRAND),
             ("grand", lambda r: r["bonus"] and r["montant"] > BONUS_GRAND))
    dist = (("< 1 km", 0.0, 1.0), ("1–2 km", 1.0, 2.0), ("2–3 km", 2.0, 3.0), ("≥ 3 km", 3.0, 99.0))
    z, nb = [], []
    for _, tb in bonus:
        ligne, ligne_n = [], []
        for _, a, b in dist:
            rows = [r["retire"] for r in T if tb(r) and a <= r["distance"] < b]
            ligne.append(sum(rows) / len(rows) if rows else 0.0)
            ligne_n.append(len(rows))
        z.append(ligne)
        nb.append(ligne_n)
    return z, [b[0] for b in bonus], [d[0] for d in dist], nb


# ---------------------------------------------------------------------------
# Rondeau et List (2008) : un premier don annoncé, un doublement promis
# ---------------------------------------------------------------------------

def _rondeau() -> dict[str, Resultat]:
    D = donnees3.rondeau()
    bras: dict[str, list[float]] = {}
    for b, d in D:
        bras.setdefault(b, []).append(d)
    oui = {k: [1 if d > 0 else 0 for d in v] for k, v in bras.items()}
    meth = f"écart de proportions ; {TIRAGES} permutations des lettres entre les deux versions"
    out = {
        "L05": _proportions("L05", oui["premier_don"], oui["temoin_haut"], "L05",
                            "premier don annoncé contre même objectif sans annonce", meth),
        "L07": _proportions("L07", oui["doublement"], oui["temoin_haut"], "L07",
                            "doublement promis contre même objectif sans promesse", meth),
        "L08": _proportions("L08", oui["premier_don"], oui["doublement"], "L08",
                            "premier don annoncé contre doublement promis", meth),
        "L09": _proportions("L09", oui["temoin_bas"], oui["temoin_haut"], "L09",
                            "objectif de 2 500 $ contre 5 000 $", meth),
    }
    a, b = bras["premier_don"], bras["temoin_haut"]
    obs, p, _ = stats.permutation(a + b, [1] * len(a) + [0] * len(b), tirages=TIRAGES, nom="L06")
    e = stats.deux_moyennes(a, b)
    lo, hi = e.ic()
    out["L06"] = Resultat(
        id="L06", effet=obs, ic=(lo, hi), p=p, n=len(a) + len(b), unite="$",
        lecture=f"{_num(e.a, 2)} $ par lettre avec l'annonce, {_num(e.b, 2)} $ sans",
        methode=f"écart de moyennes, zéros compris ; {TIRAGES} permutations des lettres",
        extra={"a": e.a, "b": e.b})
    return out


def rondeau_bras() -> dict[str, tuple[float, float, int]]:
    """Par version : part des lettres suivies d'un don, don moyen par lettre, lettres."""
    bras: dict[str, list[float]] = {}
    for b, d in donnees3.rondeau():
        bras.setdefault(b, []).append(d)
    return {k: (sum(1 for d in v if d > 0) / len(v), sum(v) / len(v), len(v)) for k, v in bras.items()}


# ---------------------------------------------------------------------------
# Cai, de Janvry et Sadoulet (2015) : le choix coché d'avance, l'explication
# ---------------------------------------------------------------------------

def _cai() -> dict[str, Resultat]:
    C = donnees3.cai()
    out = {}
    # L10 — le format par défaut, tiré au sort par hameau : on mélange les hameaux dans leur village.
    hameaux: dict[int, list[int]] = {}
    defaut_h: dict[int, int] = {}
    village_h: dict[int, int] = {}
    for r in C:
        hameaux.setdefault(r["hameau"], []).append(r["souscrit"])
        defaut_h[r["hameau"]] = r["defaut_oui"]
        village_h[r["hameau"]] = r["village"]

    def ecart(lab: dict[int, int]) -> float:
        s1 = n1 = s0 = n0 = 0
        for h, ys in hameaux.items():
            if lab[h]:
                s1 += sum(ys)
                n1 += len(ys)
            else:
                s0 += sum(ys)
                n0 += len(ys)
        return s1 / n1 - s0 / n0

    obs = ecart(defaut_h)
    par_village: dict[int, list[int]] = {}
    for h, v in village_h.items():
        par_village.setdefault(v, []).append(h)
    alea = stats.rng("L10")
    nul = []
    for _ in range(TIRAGES):
        lab = {}
        for hs in par_village.values():
            vals = [defaut_h[h] for h in hs]
            alea.shuffle(vals)
            lab.update(zip(hs, vals))
        nul.append(ecart(lab))
    sd = math.sqrt(stats.variance(nul))
    a = [r["souscrit"] for r in C if r["defaut_oui"]]
    b = [r["souscrit"] for r in C if not r["defaut_oui"]]
    pa, pb = sum(a) / len(a), sum(b) / len(b)
    out["L10"] = Resultat(
        id="L10", effet=obs * 100, ic=((obs - 1.96 * sd) * 100, (obs + 1.96 * sd) * 100), p=_perm_p(obs, nul),
        n=len(C), unite="pt",
        lecture=f"{_pct(pa)} souscrivent quand « oui » est coché d'avance, {_pct(pb)} quand c'est « non »",
        methode=(f"écart de proportions ; {TIRAGES} permutations du format entre les {len(hameaux)} hameaux, "
                 f"à l'intérieur de chaque village ; intervalle tiré de la loi nulle"),
        base=pb, relatif=(pa - pb) / pb if pb else None, extra={"a": pa, "b": pb, "na": len(a), "nb": len(b)})
    # L11 — la séance détaillée, tirée par foyer : on mélange dans le hameau.
    y = [r["souscrit"] for r in C]
    g = [r["detaillee"] for r in C]
    obs, p, _ = stats.permutation(y, g, strates=[r["hameau"] for r in C], tirages=TIRAGES, nom="L11")
    a = [r["souscrit"] for r in C if r["detaillee"]]
    b = [r["souscrit"] for r in C if not r["detaillee"]]
    e = stats.deux_proportions(sum(a), len(a), sum(b), len(b))
    lo, hi = e.ic()
    out["L11"] = Resultat(
        id="L11", effet=obs * 100, ic=(lo * 100, hi * 100), p=p, n=len(C), unite="pt",
        lecture=f"{_pct(e.a)} souscrivent après la séance détaillée, {_pct(e.b)} après la séance simple",
        methode=f"écart de proportions ; {TIRAGES} permutations dans le hameau",
        base=e.b, relatif=e.relatif, extra={"a": e.a, "b": e.b, "na": len(a), "nb": len(b)})
    return out


# ---------------------------------------------------------------------------
# Guéguen (2002) et Lynn et Mynier (1993) : la blague, la posture
# ---------------------------------------------------------------------------

def _gueguen() -> dict[str, Resultat]:
    G = donnees3.gueguen()
    par: dict[str, list[int]] = {}
    for c, t in G:
        par.setdefault(c, []).append(t)
    meth = f"écart de proportions ; {TIRAGES} permutations des cartes"
    return {
        "L12": _proportions("L12", par["blague"], par["aucune"], "L12", "blague contre aucune carte", meth),
        "L13": _proportions("L13", par["blague"], par["publicite"], "L13", "blague contre carte publicitaire", meth),
    }


def gueguen_bras() -> dict[str, tuple[float, int]]:
    par: dict[str, list[int]] = {}
    for c, t in donnees3.gueguen():
        par.setdefault(c, []).append(t)
    return {k: (sum(v) / len(v), len(v)) for k, v in par.items()}


def _lynn() -> dict[str, Resultat]:
    L = donnees3.lynn()
    y = [r["pourboire"] / r["addition"] * 100 for r in L]
    g = [r["accroupi"] for r in L]
    obs, p, _ = stats.permutation(y, g, strates=[r["midi"] for r in L], tirages=TIRAGES, nom="L14")
    a = [v for v, k in zip(y, g) if k]
    b = [v for v, k in zip(y, g) if not k]
    e = stats.deux_moyennes(a, b)
    lo, hi = e.ic()
    return {"L14": Resultat(
        id="L14", effet=obs, ic=(lo, hi), p=p, n=len(L), unite="pt de l'addition",
        lecture=f"{_num(e.a, 1)} % de l'addition en pourboire quand le serveur s'accroupit, {_num(e.b, 1)} % debout",
        methode=f"écart de moyennes ; {TIRAGES} permutations dans le service (midi, soir)",
        extra={"a": e.a, "b": e.b, "na": len(a), "nb": len(b)})}


@lru_cache(maxsize=1)
def resultats() -> dict[str, Resultat]:
    out: dict[str, Resultat] = {}
    for f in (_thornton, _rondeau, _cai, _gueguen, _lynn):
        out.update(f())
    return dict(sorted(out.items()))


def main() -> None:
    for i, r in resultats().items():
        print(f"{i} {r.effet:+.3f} [{r.ic[0]:+.3f} ; {r.ic[1]:+.3f}] p={r.p:.4f} n={r.n}  {r.lecture}")


if __name__ == "__main__":
    main()
