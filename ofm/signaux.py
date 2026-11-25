"""Les signaux — ce que RFM ne voit pas (famille S du cahier nº 3).

Un signal d'agence ne vaut que s'il dit **autre chose** que ce que tout le
monde sait déjà. Tout le monde sait qu'un fan récent, fréquent et dépensier
dépensera encore : c'est RFM, et c'est « dans le prix ». La mesure est donc
une corrélation **partielle** : on retire, du signal et de la dépense à venir,
tout ce que 27 termes de récence, fréquence, montant et ancienneté expliquent
(`base`), puis l'on corrèle les restes (`ic_partiel`). La loi nulle mélange les
restes du signal **à l'intérieur des cases RFM** : elle garde tout ce que RFM
sait et ne détruit que le lien testé.

Puis le backtest : une moitié des clients apprend deux classements, l'autre
moitié juge ; on compte la part de la dépense à venir que tient le dixième de
tête (`backtest`). C'est la règle d'agence « donner la priorité aux meilleurs
fans », rejouée sur des clients que le classement n'a jamais vus.

Les définitions sont celles du registre (`registre3.py`) : jours d'achat, au
moins deux jours dans la période d'apprentissage, fenêtre ouverte par le
premier achat et fermée par la fin de l'apprentissage.
"""

from __future__ import annotations

import bisect
import math
import operator
import random
import zlib
from datetime import date
from functools import lru_cache

from alp1.figterm import _num

from . import donnees, donnees2, donnees3, stats
from .registre3 import CLASSES_F, COUPES, NOEUDS, PART_CONTACTEE, SIGNAUX, TIRAGES
from .resultat import Resultat, entier

JEUX = ("cdnow", "retail", "x5")
MARCHE = {"cdnow": "CDNOW", "retail": "Online Retail II", "x5": "X5"}
NOM = {"groupement": "groupement", "elan": "élan", "acceleration": "accélération", "pic": "pic",
       "variete": "variété"}
#: L'hypothèse de chaque (signal, marché), et celle du backtest.
IDS = {("groupement", "cdnow"): "S01", ("groupement", "retail"): "S02", ("groupement", "x5"): "S03",
       ("elan", "cdnow"): "S04", ("elan", "retail"): "S05", ("elan", "x5"): "S06",
       ("acceleration", "cdnow"): "S07", ("acceleration", "retail"): "S08", ("acceleration", "x5"): "S09",
       ("pic", "cdnow"): "S10", ("pic", "retail"): "S11", ("pic", "x5"): "S12",
       ("variete", "retail"): "S13", ("variete", "x5"): "S14"}
BACKTEST = {"cdnow": "S15", "retail": "S16", "x5": "S17"}
RFM = ("R", "F", "M", "T")


def _ord(s: str) -> int:
    return date(int(s[:4]), int(s[5:7]), int(s[8:10])).toordinal()


@lru_cache(maxsize=None)
def jours(jeu: str) -> dict[int, tuple[tuple[int, float, int], ...]]:
    """Par client, ses jours d'achat (jour, dépense, lignes de produit), dans l'ordre."""
    acc: dict[int, dict[int, list]] = {}

    def ajouter(c: int, j: int, m: float, lignes: int) -> None:
        e = acc.setdefault(c, {}).setdefault(j, [0.0, 0])
        e[0] += m
        e[1] += lignes

    if jeu == "cdnow":
        for c, d, cd, m in donnees.cdnow():
            if m > 0:
                ajouter(c, date(d // 10000, d // 100 % 100, d % 100).toordinal(), m, cd)
    elif jeu == "retail":
        for c, d, m, lignes, annulee, _ in donnees2.retail():
            if not annulee and m > 0:
                ajouter(c, _ord(d), m, lignes)
    elif jeu == "x5":
        for c, d, m, lignes in donnees3.x5_achats():
            if m > 0:
                ajouter(c, _ord(d), m, lignes)
    else:
        raise KeyError(jeu)
    return {c: tuple(sorted((j, e[0], e[1]) for j, e in dj.items())) for c, dj in acc.items()}


def groupement(t: list[int], T: int) -> float:
    """Le groupement des achats (Zhang, Bradlow et Small, 2015), de 0 (réguliers) à 1 (en grappe).

    `t` : les jours des achats depuis le premier (t[0] = 0), `T` : la longueur
    de la fenêtre. Les n = len(t) − 1 rachats découpent [0, T + 1] en n + 1
    écarts x_i ; H = 1 + Σ x_i log x_i / log(n + 1)."""
    n = len(t) - 1
    bornes = list(t) + [T + 1]
    s = 0.0
    for a, b in zip(bornes, bornes[1:]):
        x = (b - a) / (T + 1)
        s += x * math.log(x)
    return 1.0 + s / math.log(n + 1)


def acceleration(t: list[int]) -> float | None:
    """log(écart moyen de la première moitié des écarts / celui de la seconde) ; > 0 : ça accélère."""
    ecarts = [b - a for a, b in zip(t, t[1:])]
    if len(ecarts) < 2:
        return None
    h = len(ecarts) // 2
    return math.log((sum(ecarts[:h]) / h) / (sum(ecarts[-h:]) / h))


@lru_cache(maxsize=None)
def table(jeu: str, debut: str | None = None, coupe: str | None = None, fin: str | None = None) -> tuple[dict, ...]:
    """Un client par ligne : RFM, signaux, dépense de validation. Coupe du registre par défaut."""
    d0, d1, d2 = (_ord(x) for x in (debut or COUPES[jeu][0], coupe or COUPES[jeu][1], fin or COUPES[jeu][2]))
    dern = d1 - 1
    out = []
    for c, js in jours(jeu).items():
        cal = [x for x in js if d0 <= x[0] < d1]
        if len(cal) < 2:
            continue
        F = len(cal)
        prem = cal[0][0]
        T = dern - prem
        t = [x[0] - prem for x in cal]
        dep = [x[1] for x in cal]
        total = sum(dep)
        M = total / F
        out.append({
            "client": c, "R": dern - cal[-1][0], "F": F, "M": M, "T": T,
            "y": sum(x[1] for x in js if d1 <= x[0] < d2),
            "groupement": groupement(t, T),
            "elan": sum(x[1] for x in cal if 3 * (x[0] - prem) >= 2 * T) / total,
            "acceleration": acceleration(t),
            "pic": math.log(max(dep) / M),
            "variete": math.log(sum(x[2] for x in cal) / F) if jeu != "cdnow" else None,
        })
    out.sort(key=lambda r: r["client"])
    return tuple(out)


# ---------------------------------------------------------------------------
# Retirer ce que RFM sait
# ---------------------------------------------------------------------------

def rangs(v: list[float]) -> list[float]:
    """Rangs moyens ramenés dans ]0, 1[ : (rang − 1/2)/n, ex aequo moyennés."""
    n = len(v)
    ordre = sorted(range(n), key=v.__getitem__)
    r = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and v[ordre[j + 1]] == v[ordre[i]]:
            j += 1
        m = ((i + j) / 2 + 0.5) / n
        for k in range(i, j + 1):
            r[ordre[k]] = m
        i = j + 1
    return r


def base(t: list[dict] | tuple[dict, ...]) -> list[list[float]]:
    """Les 27 termes de « ce que RFM sait » : constante, 4 × 5 morceaux de droite, 6 produits."""
    u = [rangs([c[k] for c in t]) for k in RFM]
    Z = []
    for i in range(len(t)):
        a = [u[k][i] for k in range(4)]
        row = [1.0]
        for x in a:
            row.append(x)
            row.extend(x - q if x > q else 0.0 for q in NOEUDS)
        row.extend(a[p] * a[q] for p in range(4) for q in range(p + 1, 4))
        Z.append(row)
    return Z


class Projecteur:
    """Moindres carrés sur une base fixée ; `reste(v)` rend v moins sa projection."""

    def __init__(self, Z: list[list[float]]):
        p = len(Z[0])
        G = [[0.0] * p for _ in range(p)]
        for row in Z:
            for a in range(p):
                ra = row[a]
                if ra:
                    G[a] = [g + ra * rb for g, rb in zip(G[a], row)]
        lam = 1e-9 * sum(G[a][a] for a in range(p)) / p
        for a in range(p):
            G[a][a] += lam
        self.Gi = stats.inverse(G)
        self.Z = Z

    def coef(self, v: list[float]) -> list[float]:
        zv = [0.0] * len(self.Gi)
        for row, x in zip(self.Z, v):
            if x:
                zv = [z + x * r for z, r in zip(zv, row)]
        return [sum(map(operator.mul, gi, zv)) for gi in self.Gi]

    def reste(self, v: list[float]) -> list[float]:
        b = self.coef(v)
        return [x - sum(map(operator.mul, row, b)) for row, x in zip(self.Z, v)]


def cases(t: list[dict] | tuple[dict, ...]) -> list[tuple[int, int, int]]:
    """La case RFM de chaque client : quintile de récence, classe de fréquence, quintile de montant."""
    uR, uM = rangs([c["R"] for c in t]), rangs([c["M"] for c in t])

    def classe(f: int) -> int:
        return next(i for i, (a, b) in enumerate(CLASSES_F) if a <= f <= b)

    return [(min(4, int(uR[i] * 5)), classe(c["F"]), min(4, int(uM[i] * 5))) for i, c in enumerate(t)]


def _correlation(a: list[float], b: list[float]) -> float:
    sa = math.sqrt(sum(x * x for x in a))
    sb = math.sqrt(sum(x * x for x in b))
    return sum(map(operator.mul, a, b)) / (sa * sb) if sa > 0 and sb > 0 else 0.0


def permuter(fr: list[float], yr: list[float], groupes: list, tirages: int, nom: str) -> list[float]:
    """La loi nulle : les restes du signal mélangés à l'intérieur de chaque case."""
    alea = stats.rng(nom)
    blocs: dict = {}
    for i, g in enumerate(groupes):
        blocs.setdefault(g, []).append(i)
    paires = [([fr[i] for i in idx], [yr[i] for i in idx]) for idx in blocs.values() if len(idx) > 1]
    fixe = sum(fr[i] * yr[i] for idx in blocs.values() if len(idx) == 1 for i in idx)
    norme = math.sqrt(sum(x * x for x in fr)) * math.sqrt(sum(x * x for x in yr))
    out = []
    for _ in range(tirages):
        s = fixe
        for f, y in paires:
            alea.shuffle(f)
            s += sum(map(operator.mul, f, y))
        out.append(s / norme if norme > 0 else 0.0)
    return out


def ic_partiel(t: list[dict] | tuple[dict, ...], signal: str, tirages: int = TIRAGES,
               nom: str = "ic") -> dict:
    """IC partiel d'un signal, sa loi nulle, et la part du signal que RFM explique déjà."""
    t = [c for c in t if c[signal] is not None]
    Z = base(t)
    proj = Projecteur(Z)
    f, y = rangs([c[signal] for c in t]), rangs([c["y"] for c in t])
    fr, yr = proj.reste(f), proj.reste(y)
    rho = _correlation(fr, yr)
    nul = permuter(fr, yr, cases(t), tirages, nom)
    # La loi nulle n'est pas centrée sur zéro : les cases RFM gardent le lien qu'elles portent entre les
    # restes (ce que 27 termes lisses n'ont pas rendu). L'effet est l'écart à son centre, le test aussi.
    centre = sum(nul) / len(nul)
    sd = math.sqrt(sum((v - centre) ** 2 for v in nul) / (len(nul) - 1))
    effet = rho - centre
    k = sum(1 for v in nul if abs(v - centre) >= abs(effet) - 1e-15)
    mf = sum(f) / len(f)
    r2 = 1.0 - sum(x * x for x in fr) / sum((x - mf) ** 2 for x in f)
    return {"rho": rho, "centre": centre, "effet": effet, "p": (k + 1) / (tirages + 1), "n": len(t),
            "r2": r2, "ic": (effet - 1.96 * sd, effet + 1.96 * sd),
            "nul_bas": stats.quantile(nul, 0.025) - centre, "nul_haut": stats.quantile(nul, 0.975) - centre,
            "reste_signal": fr, "reste_y": yr}


# ---------------------------------------------------------------------------
# Le backtest : le dixième de tête, sur des clients jamais vus
# ---------------------------------------------------------------------------

def _moitie(jeu: str, client: int) -> int:
    return zlib.crc32(f"{jeu}:{client}".encode("utf-8")) % 2


def _colonnes_signaux(t: list[dict] | tuple[dict, ...], jeu: str) -> list[list[float]]:
    """Les signaux en rangs ; l'accélération absente vaut 1/2 et une indicatrice le dit."""
    cols = []
    for s in SIGNAUX[jeu]:
        idx = [i for i, c in enumerate(t) if c[s] is not None]
        r = rangs([t[i][s] for i in idx])
        col = [0.5] * len(t)
        for i, v in zip(idx, r):
            col[i] = v
        cols.append(col)
        if len(idx) < len(t):
            cols.append([0.0 if t[i][s] is not None else 1.0 for i in range(len(t))])
    return [list(x) for x in zip(*cols)]


def _ajuster(X: list[list[float]], y: list[float]) -> list[float]:
    return Projecteur(X).coef(y)


def _score(X: list[list[float]], b: list[float]) -> list[float]:
    return [sum(map(operator.mul, row, b)) for row in X]


def _ordre(scores: list[float], clients: list[int]) -> list[int]:
    return sorted(range(len(scores)), key=lambda i: (-scores[i], clients[i]))


def capture(ordre: list[int], y: list[float], part: float = PART_CONTACTEE,
            poids: list[int] | None = None) -> float:
    """Part de la dépense tenue par la tête du classement (poids de rééchantillonnage possibles)."""
    if poids is None:
        k = math.ceil(part * len(ordre))
        tot = sum(y)
        return sum(y[i] for i in ordre[:k]) / tot if tot > 0 else 0.0
    W = sum(poids)
    seuil = part * W
    cum = haut = 0.0
    for i in ordre:
        if cum >= seuil:
            break
        w = poids[i]
        cum += w
        haut += w * y[i]
    tot = sum(w * v for w, v in zip(poids, y))
    return haut / tot if tot > 0 else 0.0


@lru_cache(maxsize=None)
def backtest(jeu: str, tirages: int = TIRAGES) -> dict:
    t = table(jeu)
    Z = base(t)
    S = _colonnes_signaux(t, jeu)
    X = [z + s for z, s in zip(Z, S)]
    A = [i for i, c in enumerate(t) if _moitie(jeu, c["client"]) == 0]
    B = [i for i, c in enumerate(t) if _moitie(jeu, c["client"]) == 1]
    yA = rangs([t[i]["y"] for i in A])
    b_rfm = _ajuster([Z[i] for i in A], yA)
    b_sig = _ajuster([X[i] for i in A], yA)
    clients = [t[i]["client"] for i in B]
    y = [t[i]["y"] for i in B]
    s_rfm, s_sig = _score([Z[i] for i in B], b_rfm), _score([X[i] for i in B], b_sig)
    o_rfm, o_sig = _ordre(s_rfm, clients), _ordre(s_sig, clients)
    o_gros = _ordre([t[i]["M"] * t[i]["F"] for i in B], clients)          # la liste des gros dépensiers
    o_vrai = _ordre(y, clients)                                            # ce qu'aurait fait un devin
    c_rfm, c_sig = capture(o_rfm, y), capture(o_sig, y)
    # Rééchantillonnage apparié des clients jugés : poids de Poisson de moyenne 1.
    alea = stats.rng(f"backtest-{jeu}")
    cdf, acc, f = [], 0.0, math.exp(-1.0)
    for k in range(12):
        acc += f
        cdf.append(acc)
        f /= k + 1
    deltas = []
    for _ in range(tirages):
        w = [bisect.bisect(cdf, alea.random()) for _ in B]
        deltas.append(capture(o_sig, y, poids=w) - capture(o_rfm, y, poids=w))
    d = c_sig - c_rfm
    k_bas = sum(1 for v in deltas if v <= 0)
    k_haut = sum(1 for v in deltas if v >= 0)
    p = min(1.0, 2 * (1 + min(k_bas, k_haut)) / (tirages + 1))
    parts = [k / 100 for k in range(1, 51)]
    return {"n_a": len(A), "n_b": len(B), "rfm": c_rfm, "signaux": c_sig, "delta": d, "p": p,
            "ic": (stats.quantile(deltas, 0.025), stats.quantile(deltas, 0.975)),
            "gros": capture(o_gros, y), "devin": capture(o_vrai, y),
            "courbes": {"parts": parts,
                        "gros": [capture(o_gros, y, q) for q in parts],
                        "rfm": [capture(o_rfm, y, q) for q in parts],
                        "signaux": [capture(o_sig, y, q) for q in parts],
                        "devin": [capture(o_vrai, y, q) for q in parts]},
            "depense_b": sum(y)}


# ---------------------------------------------------------------------------
# Résultats du registre
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def mesure(signal: str, jeu: str) -> dict:
    return ic_partiel(table(jeu), signal, nom=f"{signal}-{jeu}")


def _r(v: float) -> str:
    return ("+" if v >= 0 else "−") + _num(abs(v), 3)


@lru_cache(maxsize=1)
def resultats() -> dict[str, Resultat]:
    out: dict[str, Resultat] = {}
    for (signal, jeu), i in IDS.items():
        m = mesure(signal, jeu)
        out[i] = Resultat(
            id=i, effet=m["effet"], ic=m["ic"], p=m["p"], n=m["n"], unite="r",
            lecture=(f"IC partiel {_r(m['effet'])} au-delà de RFM, sur {entier(m['n'])} clients de {MARCHE[jeu]} ; "
                     f"RFM explique déjà {_num(m['r2'] * 100, 0)} % du signal ; 95 % du hasard "
                     f"tient entre {_r(m['nul_bas'])} et {_r(m['nul_haut'])}"),
            methode=(f"corrélation des rangs entre les restes du signal et de la dépense de validation, "
                     f"27 termes RFM retirés, moins le centre de la loi nulle ({_r(m['centre'])}) ; "
                     f"{TIRAGES} mélanges des restes dans les cases RFM"),
            extra={"r2": m["r2"], "nul_bas": m["nul_bas"], "nul_haut": m["nul_haut"], "signal": signal,
                   "jeu": jeu, "rho": m["rho"], "centre": m["centre"]})
    for jeu, i in BACKTEST.items():
        b = backtest(jeu)
        out[i] = Resultat(
            id=i, effet=b["delta"] * 100, ic=(b["ic"][0] * 100, b["ic"][1] * 100), p=b["p"], n=b["n_b"],
            unite="pt",
            lecture=(f"le dixième de tête tient {_num(b['signaux'] * 100, 1)} % de la dépense à venir avec les "
                     f"signaux, {_num(b['rfm'] * 100, 1)} % avec RFM seul ({_num(b['gros'] * 100, 1)} % pour la "
                     f"liste des gros dépensiers, {_num(b['devin'] * 100, 1)} % pour un devin), "
                     f"{entier(b['n_b'])} clients jugés"),
            methode=(f"deux classements appris sur {entier(b['n_a'])} clients, jugés sur les {entier(b['n_b'])} "
                     f"autres ; {TIRAGES} rééchantillonnages appariés (poids de Poisson)"),
            extra={k: b[k] for k in ("rfm", "signaux", "gros", "devin", "n_a", "n_b")})
    return out


# ---------------------------------------------------------------------------
# Pour les graphiques : le signal à travers le temps, et la grille d'un relief
# ---------------------------------------------------------------------------

GLISSANT = {
    "cdnow": ("1997-01-01", ("1997-07-01", "1997-08-01", "1997-09-01", "1997-10-01", "1997-11-01",
                             "1997-12-01", "1998-01-01"), 182),
    "retail": ("2009-12-01", ("2010-06-01", "2010-08-01", "2010-10-01", "2010-12-01", "2011-02-01",
                              "2011-04-01", "2011-06-01"), 182),
}


@lru_cache(maxsize=None)
def glissant(jeu: str, tirages: int = 199) -> list[dict]:
    """L'IC partiel de chaque signal à chaque coupe (validation de 26 semaines), et sa bande nulle."""
    debut, coupes, duree = GLISSANT[jeu]
    out = []
    for coupe in coupes:
        fin = date.fromordinal(_ord(coupe) + duree).isoformat()
        t = table(jeu, debut, coupe, fin)
        ligne = {"coupe": coupe, "n": len(t)}
        for s in SIGNAUX[jeu]:
            m = ic_partiel(t, s, tirages=tirages, nom=f"gl-{jeu}-{s}-{coupe}")
            ligne[s] = (m["effet"], m["nul_bas"], m["nul_haut"])
        out.append(ligne)
    return out


def grille(signal: str, jeu: str, k: int = 5) -> tuple[list[list[float]], int]:
    """Dépense à venir moyenne (rapportée à la moyenne) par quintile RFM et quintile du reste du signal."""
    t = [c for c in table(jeu) if c[signal] is not None]
    Z = base(t)
    proj = Projecteur(Z)
    yr = rangs([c["y"] for c in t])
    prevu = [a - b for a, b in zip(yr, proj.reste(yr))]
    fr = mesure(signal, jeu)["reste_signal"]
    q_rfm, q_sig = rangs(prevu), rangs(fr)
    moy = sum(c["y"] for c in t) / len(t)
    som = [[0.0] * k for _ in range(k)]
    nb = [[0] * k for _ in range(k)]
    for i, c in enumerate(t):
        a, b = min(k - 1, int(q_rfm[i] * k)), min(k - 1, int(q_sig[i] * k))
        som[a][b] += c["y"]
        nb[a][b] += 1
    return [[som[a][b] / nb[a][b] / moy if nb[a][b] else 0.0 for b in range(k)] for a in range(k)], len(t)


def main() -> None:
    for i, r in resultats().items():
        print(f"{i} {r.effet:+.4f} [{r.ic[0]:+.4f} ; {r.ic[1]:+.4f}] p={r.p:.4f} n={r.n}  {r.lecture[:120]}")


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# Vérité connue : la mesure se trompe-t-elle aussi souvent qu'elle l'annonce ?
# ---------------------------------------------------------------------------

def verite(n: int, effet: float, graine: int) -> list[dict]:
    """Des clients dont la dépense à venir ne dépend que de RFM, plus `effet` fois la part cachée du signal.

    Le signal est une fonction **non linéaire** de RFM (récence rapportée à l'ancienneté, log de la
    fréquence) plus une part cachée h. À `effet` = 0, le signal ne dit rien que RFM ne sache : un
    test juste le déclare vide 95 fois sur 100, malgré tout ce qu'il partage avec RFM."""
    rnd = random.Random(graine)
    t = []
    for i in range(n):
        F = 2 + int(rnd.expovariate(0.45))
        T = rnd.randint(30, 300)
        R = int(rnd.random() * T)
        M = math.exp(rnd.gauss(3.0, 0.7))
        h = rnd.gauss(0.0, 1.0)
        s = math.sin(3.0 * R / T) + 0.35 * math.log(F) + 0.4 * math.log(M) + 0.6 * h
        mu = math.exp(-R / 60.0) * F * M / 25.0 * math.exp(effet * h)
        y = rnd.expovariate(1.0 / mu) if rnd.random() < 0.65 else 0.0
        t.append({"client": i, "R": R, "F": F, "M": M, "T": T, "y": y, "sig": s})
    return t


def verite_dure(n: int, graine: int) -> list[dict]:
    """Le cas difficile : signal et dépense dépendent **brutalement** de la récence (un seuil à 10 jours,
    une décroissance en 8 jours), plus finement que les morceaux de droite ne savent le rendre. Le
    signal ne dit rien de plus que RFM."""
    rnd = random.Random(graine)
    t = []
    for i in range(n):
        F = 2 + int(rnd.expovariate(0.45))
        T = rnd.randint(30, 300)
        R = int(rnd.random() * T)
        M = math.exp(rnd.gauss(3.0, 0.7))
        s = math.exp(-R / 8.0) * 3 + 0.5 * math.log(F) * (R < 20) + rnd.gauss(0.0, 0.5)
        mu = (3.0 if R < 10 else math.exp(-R / 40.0)) * F * M / 25.0
        y = rnd.expovariate(1.0 / mu) if rnd.random() < 0.65 else 0.0
        t.append({"client": i, "R": R, "F": F, "M": M, "T": T, "y": y, "sig": s})
    return t


def etalonnage(essais: int = 100, n: int = 1500, effet: float = 0.0, tirages: int = 199,
               dur: bool = False) -> tuple[int, int]:
    """Combien d'essais sur `essais` le test déclare au seuil de 5 %."""
    k = 0
    for e in range(essais):
        t = verite_dure(n, 500 + e) if dur else verite(n, effet, 1000 + e)
        m = ic_partiel(t, "sig", tirages=tirages, nom=f"{'dur' if dur else 'verite'}-{e}")
        k += m["p"] < 0.05
    return k, essais
