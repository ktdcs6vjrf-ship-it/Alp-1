"""Famille A — apprendre chez soi, contre les règles de la foule.

Une agence tire au sort, sur une partie de sa base (le **pilote**), qui reçoit
un message et qui n'en reçoit pas ; elle apprend de ce tirage **à qui le
message change quelque chose** ; puis elle écrit au tiers de la base restante
qu'elle juge le plus sensible. On mesure ce qu'elle gagne, au même nombre de
messages, contre ce que gagnent les règles de la foule (`registre4.REGLES`) :
les plus gros dépensiers d'abord, les plus à risque d'abord, ou le hasard.

Le juge est commun à tous les réglages : la moitié de la base qui n'a jamais
servi à apprendre (u ≥ 0,5). Le tirage au sort des trois expériences
(Hillstrom, Lenta, X5) rend la mesure exacte : dans n'importe quel groupe de
clients choisi sans regarder l'issue, l'écart entre écrits et non-écrits est
l'effet du message dans ce groupe.

Tout passe par des sommes par groupe (`registre4.GROUPES` groupes tirés au
hasard parmi les clients jugés) : l'écart-type d'un gain, la loi jointe des 36
réglages pour le test SPA et la performance par bloc du CSCV s'en déduisent
sans repasser sur les 687 029 clients de Lenta.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from functools import lru_cache
from itertools import compress

from . import cibler, registre2, stats, stress
from . import registre4 as R4
from .resultat import Resultat, entier

JEUX = ("hillstrom", "lenta", "x5")
#: Les variables lues pour les règles et le placebo, dans les lignes de `cibler`.
_VALEUR = {"hillstrom": "log_historique", "lenta": "log_depense_12m", "x5": "log_depense"}
QUOI = {"hillstrom": "visites", "lenta": "visites", "x5": "achats"}
NOM_REGLE = {"valeur": "les plus gros dépensiers", "risque": "les plus à risque", "hasard": "le hasard"}
IDS = {
    ("valeur", "hillstrom"): "A01", ("valeur", "lenta"): "A02", ("valeur", "x5"): "A03",
    ("risque", "hillstrom"): "A04", ("risque", "lenta"): "A05", ("risque", "x5"): "A06",
    ("hasard", "hillstrom"): "A07", ("hasard", "lenta"): "A08", ("hasard", "x5"): "A09",
}
IDS_MODE = {"hillstrom": "A10", "lenta": "A11", "x5": "A12"}


# ---------------------------------------------------------------------------
# Les données d'un jeu, en colonnes
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def donnees(jeu: str) -> dict:
    rows = cibler.JEUX[jeu]()
    noms = registre2.VARIABLES[jeu]
    X = {v: [r[0][v] for r in rows] for v in noms}
    out = {"n": len(rows), "noms": noms, "X": X, "t": [r[1] for r in rows], "y": [r[2] for r in rows],
           "valeur": [r[0][_VALEUR[jeu]] for r in rows],
           "placebo": [float(r[0][R4.PLACEBO[jeu]] or 0.0) for r in rows]}
    if jeu == "hillstrom":
        X["hf"] = [f"{int(r[0]['hommes'])}{int(r[0]['femmes'])}" for r in rows]
    if jeu == "lenta":
        X["sexe"] = ["f" if r[0]["sexe_f"] else ("m" if r[0]["sexe_m"] else "u") for r in rows]
    # Un ordre tiré au sort, une fois pour toutes : il départage les ex aequo et fait la règle du hasard.
    alea = stats.rng(f"a-ordre-{jeu}")
    out["cle"] = [alea.random() for _ in rows]
    return out


@lru_cache(maxsize=None)
def coupe(jeu: str, graine: int = 0) -> dict:
    """Le tirage u (pilote si u < π, jugé si u ≥ 0,5) et les groupes des clients jugés."""
    d = donnees(jeu)
    alea = stats.rng(f"a-u-{jeu}-{graine}")
    u = [alea.random() for _ in range(d["n"])]
    juges = [i for i in range(d["n"]) if u[i] >= 0.5]
    ag = stats.rng(f"a-groupe-{jeu}-{graine}")
    groupe = [int(ag.random() * R4.GROUPES) for _ in juges]
    return {"u": u, "juges": juges, "groupe": groupe}


# ---------------------------------------------------------------------------
# Apprendre sur le pilote
# ---------------------------------------------------------------------------

def _colonnes(d: dict, pilote: list[bool]) -> list[list[float]]:
    """Constante, variables (valeur manquante : médiane du pilote) et indicatrices d'absence."""
    cols = [[1.0] * d["n"]]
    absences: list[list[float]] = []
    for v in d["noms"]:
        brut = d["X"][v]
        vus = [x for x, p in zip(brut, pilote) if p and x is not None]
        med = stats.quantile(vus, 0.5)
        cols.append([med if x is None else float(x) for x in brut])
        if any(x is None for x in brut):
            ind = [1.0 if x is None else 0.0 for x in brut]
            if ind not in absences:
                absences.append(ind)
                cols.append(ind)
    return cols


def _mco(jeu: str, graine: int, pilote_part: float, issue: str) -> tuple[list[float], list[float]]:
    """Deux régressions linéaires (une par bras) sur le pilote : effet et risque estimés des jugés."""
    d, c = donnees(jeu), coupe(jeu, graine)
    y = d[issue] if issue != "y" else d["y"]
    pilote = [x < pilote_part for x in c["u"]]
    cols = _colonnes(d, pilote)
    m1 = [p and t == 1 for p, t in zip(pilote, d["t"])]
    m0 = [p and t == 0 for p, t in zip(pilote, d["t"])]
    b1 = cibler.ols([list(compress(col, m1)) for col in cols], list(compress(y, m1)))
    b0 = cibler.ols([list(compress(col, m0)) for col in cols], list(compress(y, m0)))
    J = c["juges"]
    cj = [[col[i] for i in J] for col in cols]
    p1, p0 = cibler._predire(cj, b1), cibler._predire(cj, b0)
    return [a - b for a, b in zip(p1, p0)], [1.0 - b for b in p0]


def _classe(valeurs: list, pilote: list[bool], regle) -> list:
    """La classe de chaque client pour une variable de case (bornes tirées du pilote)."""
    if regle == "val":
        return list(valeurs)
    if isinstance(regle, tuple):
        return [-1 if v is None else bisect_right(regle, v) for v in valeurs]
    k = {"q5": 5, "q3": 3}[regle]
    vus = sorted(v for v, p in zip(valeurs, pilote) if p and v is not None)
    bornes = [vus[min(len(vus) - 1, int(len(vus) * j / k))] for j in range(1, k)]
    return [-1 if v is None else bisect_right(bornes, v) for v in valeurs]


def _cases(jeu: str, graine: int, pilote_part: float, modele: str, issue: str) -> list[float]:
    """Effet par case, estimé sur le pilote, rétréci vers l'effet moyen du pilote."""
    d, c = donnees(jeu), coupe(jeu, graine)
    y = d[issue] if issue != "y" else d["y"]
    pilote = [x < pilote_part for x in c["u"]]
    classes = [_classe(d["X"][v], pilote, r) for v, r in R4.CASES[jeu][modele]]
    case = list(zip(*classes))
    acc: dict = {}
    n1 = s1 = n0 = s0 = 0
    for i in range(d["n"]):
        if not pilote[i]:
            continue
        e = acc.setdefault(case[i], [0, 0.0, 0, 0.0])
        if d["t"][i]:
            e[0] += 1
            e[1] += y[i]
            n1 += 1
            s1 += y[i]
        else:
            e[2] += 1
            e[3] += y[i]
            n0 += 1
            s0 += y[i]
    moyen = s1 / n1 - s0 / n0
    effet = {}
    for k, (a1, b1, a0, b0) in acc.items():
        if a1 == 0 or a0 == 0:
            effet[k] = moyen
            continue
        neff = a1 * a0 / (a1 + a0)
        effet[k] = (neff * (b1 / a1 - b0 / a0) + R4.RETRECI * moyen) / (neff + R4.RETRECI)
    return [effet.get(case[i], moyen) for i in c["juges"]]


@lru_cache(maxsize=None)
def scores(jeu: str, graine: int, pilote_part: float, modele: str, issue: str = "y") -> dict:
    """Les scores des clients jugés : politique apprise et règles de la foule."""
    d, c = donnees(jeu), coupe(jeu, graine)
    J = c["juges"]
    effet_mco, risque = _mco(jeu, graine, pilote_part, issue)
    appris = effet_mco if modele == "mco" else _cases(jeu, graine, pilote_part, modele, issue)
    valeur = [(-math.inf if d["valeur"][i] is None else d["valeur"][i]) for i in J]
    return {"appris": appris, "risque": risque, "valeur": valeur, "hasard": [d["cle"][i] for i in J]}


def choisir(score: list[float], cle: list[float], part: float) -> list[bool]:
    """Les `part` clients de plus haut score ; les ex aequo sont départagés par l'ordre tiré au sort."""
    k = int(round(len(score) * part))
    ordre = sorted(range(len(score)), key=lambda i: (-score[i], cle[i]))[:k]
    m = [False] * len(score)
    for i in ordre:
        m[i] = True
    return m


# ---------------------------------------------------------------------------
# Gains et sommes par groupe
# ---------------------------------------------------------------------------

def _sommes(jeu: str, graine: int, membre: list[bool], issue: str = "y") -> list[list[float]]:
    """Par groupe : (n₁, s₁, n₀, s₀) des clients choisis."""
    d, c = donnees(jeu), coupe(jeu, graine)
    y = d[issue] if issue != "y" else d["y"]
    t = d["t"]
    G = R4.GROUPES
    n1, s1, n0, s0 = [0.0] * G, [0.0] * G, [0.0] * G, [0.0] * G
    for j, (i, g) in enumerate(zip(c["juges"], c["groupe"])):
        if not membre[j]:
            continue
        if t[i]:
            n1[g] += 1
            s1[g] += y[i]
        else:
            n0[g] += 1
            s0[g] += y[i]
    return [n1, s1, n0, s0]


def _tau_inf(S: list[list[float]]) -> tuple[float, list[float]]:
    """Effet du message dans l'ensemble choisi, et sa fonction d'influence par groupe."""
    n1, s1, n0, s0 = (sum(x) for x in S)
    p1, p0 = s1 / n1, s0 / n0
    inf = [(b - p1 * a) / n1 - (dd - p0 * cc) / n0 for a, b, cc, dd in zip(*S)]
    return p1 - p0, inf


def _par_bloc(S: list[list[float]]) -> list[float]:
    """L'effet du message dans chaque bloc du CSCV (groupe modulo `BLOCS`)."""
    B = R4.BLOCS
    acc = [[0.0] * 4 for _ in range(B)]
    for g in range(len(S[0])):
        b = g % B
        for k in range(4):
            acc[b][k] += S[k][g]
    return [(a[1] / a[0] - a[3] / a[2]) if a[0] and a[2] else 0.0 for a in acc]


@lru_cache(maxsize=None)
def _masque(jeu: str, graine: int, pilote_part: float, modele: str, issue: str, quoi: str,
            budget: float) -> tuple[tuple[bool, ...], tuple]:
    """Les clients choisis par une politique, et leurs sommes par groupe (gardés en mémoire)."""
    # Les règles « valeur » et « hasard » ne dépendent ni du pilote ni du modèle.
    sc = scores(jeu, graine, pilote_part, modele, issue)
    m = choisir(sc[quoi], sc["hasard"], budget)
    return tuple(m), tuple(tuple(x) for x in _sommes(jeu, graine, m, issue))


def _cle(pilote_part, modele, quoi):
    if quoi in ("valeur", "hasard"):
        return R4.PILOTE, R4.MODELE
    if quoi == "risque":
        return pilote_part, R4.MODELE
    return pilote_part, modele


def comparer(jeu: str, graine: int, pilote_part: float, modele: str, budget: float, regle: str,
             issue: str = "y", contre: str = "appris") -> dict:
    """Gain de `contre` (par défaut la politique apprise) moins gain de `regle`, en points pour 100 jugés."""
    ma, Sa = _masque(jeu, graine, *_cle(pilote_part, modele, contre), issue, contre, budget)
    mb, Sb = _masque(jeu, graine, *_cle(pilote_part, modele, regle), issue, regle, budget)
    Sa, Sb = [list(x) for x in Sa], [list(x) for x in Sb]
    ta, ia = _tau_inf(Sa)
    tb, ib = _tau_inf(Sb)
    fac = 100.0 * sum(ma) / len(ma)
    d = fac * (ta - tb)
    inf = [fac * (u - v) for u, v in zip(ia, ib)]
    se = math.sqrt(sum(v * v for v in inf))
    blocs = [fac * (u - v) for u, v in zip(_par_bloc(Sa), _par_bloc(Sb))]
    return {"d": d, "se": se, "p": stats.p_bilateral(d / se) if se > 0 else 1.0, "inf": inf,
            "blocs": blocs, "gain_a": fac * ta, "gain_b": fac * tb, "n": len(ma),
            "commun": sum(1 for a, b in zip(ma, mb) if a and b), "k": sum(ma)}


def specs() -> list[tuple[float, float, str]]:
    return [(p, b, m) for p in R4.PILOTES for b in R4.BUDGETS for m in R4.MODELES]


# ---------------------------------------------------------------------------
# Les résultats et leur batterie
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def principal(jeu: str, regle: str) -> dict:
    return comparer(jeu, 0, R4.PILOTE, R4.MODELE, R4.BUDGET, regle)


@lru_cache(maxsize=None)
def batterie(jeu: str, regle: str) -> dict:
    """Autres coupes, courbe de spécification, SPA, CSCV et placebo d'une comparaison."""
    mode = regle == "mode"  # la règle des gros dépensiers contre le hasard (A10–A12)
    if mode:
        coupes = [comparer(jeu, g, R4.PILOTE, R4.MODELE, R4.BUDGET, "hasard", contre="valeur")["d"]
                  for g in range(R4.COUPES_EN_PLUS + 1)]
        spec = [comparer(jeu, 0, R4.PILOTE, R4.MODELE, b, "hasard", contre="valeur") for b in R4.BUDGETS]
        placebo = comparer(jeu, 0, R4.PILOTE, R4.MODELE, R4.BUDGET, "hasard", issue="placebo", contre="valeur")
        return {"coupes": coupes, "spec": [(r["d"], r["p"]) for r in spec], "spec_noms": list(R4.BUDGETS),
                "placebo": (placebo["d"], placebo["p"])}
    coupes = [comparer(jeu, g, R4.PILOTE, R4.MODELE, R4.BUDGET, regle)["d"] for g in range(R4.COUPES_EN_PLUS + 1)]
    tous = [comparer(jeu, 0, p, m, b, regle) for p, b, m in specs()]
    sp = stress.spa([r["d"] for r in tous], [r["inf"] for r in tous], R4.TIRAGES, f"a-{jeu}-{regle}")
    cs = stress.cscv([r["blocs"] for r in tous])
    placebo = comparer(jeu, 0, R4.PILOTE, R4.MODELE, R4.BUDGET, regle, issue="placebo")
    return {"coupes": coupes, "spec": [(r["d"], r["p"]) for r in tous], "spec_noms": specs(),
            "spa": {k: v for k, v in sp.items()}, "cscv": {k: cs[k] for k in ("pbo", "perte", "combinaisons")},
            "cscv_degradation": cs["degradation"][::97], "placebo": (placebo["d"], placebo["p"])}


def _resultat(rid: str, jeu: str, regle: str) -> Resultat:
    if regle == "mode":
        r = comparer(jeu, 0, R4.PILOTE, R4.MODELE, R4.BUDGET, "hasard", contre="valeur")
        qui, contre = "les gros dépensiers", "le hasard"
    else:
        r = principal(jeu, regle)
        qui, contre = "la politique apprise", NOM_REGLE[regle]
    lecture = (f"{qui} gagne {r['gain_a']:+.2f} {QUOI[jeu]} pour 100 clients, {contre} {r['gain_b']:+.2f} "
               f"(un tiers de la base écrit, {entier(r['n'])} clients jamais vus par l'apprentissage)"
               ).replace(".", ",")
    return Resultat(id=rid, effet=r["d"], ic=(r["d"] - 1.96 * r["se"], r["d"] + 1.96 * r["se"]), p=r["p"],
                    n=r["n"], unite="pt", lecture=lecture,
                    methode="tirage au sort ; fonction d'influence sommée par groupe (1 000 groupes)",
                    extra={"gain_a": r["gain_a"], "gain_b": r["gain_b"], "commun": r["commun"], "k": r["k"],
                           "se": r["se"]})


@lru_cache(maxsize=1)
def resultats() -> dict[str, Resultat]:
    out = {}
    for (regle, jeu), rid in IDS.items():
        out[rid] = _resultat(rid, jeu, regle)
    for jeu, rid in IDS_MODE.items():
        out[rid] = _resultat(rid, jeu, "mode")
    return dict(sorted(out.items()))


@lru_cache(maxsize=1)
def batteries() -> dict[str, dict]:
    out = {rid: batterie(jeu, regle) for (regle, jeu), rid in IDS.items()}
    out.update({rid: batterie(jeu, "mode") for jeu, rid in IDS_MODE.items()})
    return dict(sorted(out.items()))


def rapports() -> dict[str, float]:
    """Pour l'arène (`registre4.CALAGE`) : gain appris / hasard et gain des gros dépensiers / hasard."""
    ra, rv = [], []
    for jeu in JEUX:
        h = principal(jeu, "hasard")
        ra.append(h["gain_a"] / h["gain_b"])
        v = comparer(jeu, 0, R4.PILOTE, R4.MODELE, R4.BUDGET, "hasard", contre="valeur")
        rv.append(v["gain_a"] / v["gain_b"])
    return {"appris": sum(ra) / 3, "valeur": sum(rv) / 3, "par_jeu_appris": ra, "par_jeu_valeur": rv}


# ---------------------------------------------------------------------------
# Vérité connue : la chaîne entière sur des issues simulées
# ---------------------------------------------------------------------------

def etalonner(essais: int = 100, heterogene: bool = False) -> dict:
    """La chaîne de la famille A sur Hillstrom, l'issue remplacée par une issue simulée de vérité connue.

    Sans hétérogénéité, le message fait partout le même effet : la politique
    apprise ne peut pas battre le hasard, et le test ne doit conclure que dans
    5 % des cas au plus. Avec hétérogénéité (effet croissant avec l'historique),
    on compte combien de fois l'intervalle à 95 % contient le vrai gain."""
    d = donnees("hillstrom")
    base_p0 = 0.10
    z = d["X"]["log_historique"]
    m = sum(z) / len(z)
    s = math.sqrt(sum((v - m) ** 2 for v in z) / len(z))
    tau = [0.06 * (1 + (1.2 * (v - m) / s if heterogene else 0.0)) for v in z]
    tau = [min(0.3, max(-0.05, v)) for v in tau]
    rejets = couverts = 0
    for e in range(essais):
        alea = stats.rng(f"a-etal-{heterogene}-{e}")
        sim = [1.0 if alea.random() < base_p0 + (tau[i] if d["t"][i] else 0.0) else 0.0 for i in range(d["n"])]
        d["sim"] = sim
        scores.cache_clear()
        _masque.cache_clear()
        r = comparer("hillstrom", 0, R4.PILOTE, R4.MODELE, R4.BUDGET, "hasard", issue="sim")
        sc = scores("hillstrom", 0, R4.PILOTE, R4.MODELE, "sim")
        J = coupe("hillstrom", 0)["juges"]
        ma, mb = choisir(sc["appris"], sc["hasard"], R4.BUDGET), choisir(sc["hasard"], sc["hasard"], R4.BUDGET)
        vrai = 100.0 * R4.BUDGET * (sum(tau[i] for i, a in zip(J, ma) if a) / sum(ma)
                                     - sum(tau[i] for i, b in zip(J, mb) if b) / sum(mb))
        rejets += r["p"] < 0.05 and r["d"] > 0
        couverts += r["d"] - 1.96 * r["se"] <= vrai <= r["d"] + 1.96 * r["se"]
    d.pop("sim", None)
    scores.cache_clear()
    _masque.cache_clear()
    return {"essais": essais, "heterogene": heterogene, "conclut": rejets / essais, "couverture": couverts / essais}


def main() -> None:
    from .registre4 import par_id
    reg = par_id()
    for i, r in resultats().items():
        print(f"{i} {reg[i].enonce[:58]:58s} {r.effet:+7.3f} pt [{r.ic[0]:+.3f}, {r.ic[1]:+.3f}] p={r.p:.2e}")
        print("     ", r.lecture)


if __name__ == "__main__":
    main()
