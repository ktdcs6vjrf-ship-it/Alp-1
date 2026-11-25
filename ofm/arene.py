"""L'arène — 200 agences qui pensent à différents niveaux, s'imitent et se disputent les créatrices.

C'est l'outil « à nous » du cahier : il ne mesure rien du monde, il vérifie
qu'une conclusion **ne dépend pas d'un réglage précis**. Le modèle est fixé
dans `registre4` (avant le calcul) ; ses dix-huit paramètres inconnus sont tirés
en hypercube latin sur le domaine déclaré, 400 fois. Pour chaque tirage, la même
arène (mêmes concurrents, même bruit, même date de contrôle) est rejouée quatre
fois, l'agence de l'utilisateur jouant tour à tour chacune des quatre
stratégies : on compare donc des stratégies, pas des chances.

Lecture stricte du registre, dite ici : le **témoin** ne reçoit aucun message de
campagne (sa part du revenu du chat est perdue), et tout le revenu du chat est
sensible au ciblage. La seconde hypothèse est généreuse pour l'apprentissage ;
`variante_severe` rejoue l'arène en ne laissant le ciblage agir que sur la
moitié du revenu du chat (variante non déclarée, donnée pour information).

Les deux rapports du ciblage ne sont pas tirés : ils viennent des mesures de la
famille A (`avances.rapports`) — apprendre chez soi contre le hasard, gros
dépensiers contre le hasard.
"""

from __future__ import annotations

import math
from functools import lru_cache

from . import avances, stats, stress
from . import registre4 as R4

FOCALE = R4.AGENCES  # l'indice de l'agence de l'utilisateur


@lru_cache(maxsize=1)
def calage() -> dict:
    r = avances.rapports()
    return {"appris": r["appris"], "valeur": r["valeur"]}


@lru_cache(maxsize=1)
def tirages() -> list[dict]:
    return stress.hypercube(R4.DOMAINE, R4.TIRAGES_ARENE, "arene")


def _poisson_tronque(alea, tau: float) -> int:
    u, k, p = alea.random(), 0, math.exp(-tau)
    acc = p
    while u > acc and k < 3:
        k += 1
        p *= tau / k
        acc += p
    return k


@lru_cache(maxsize=None)
def _hasard(i: int, part_niveau2: float | None) -> dict:
    """Tout l'aléa d'un tirage, fixé une fois : niveaux et tailles de départ, bruit, imitation, contrôle."""
    th = tirages()[i]
    alea = stats.rng(f"arene-{i}-{part_niveau2}")
    N = R4.AGENCES
    niveaux = []
    for a in range(N):
        if part_niveau2 is not None and a < round(part_niveau2 * N):
            niveaux.append(2)
        else:
            niveaux.append(_poisson_tronque(alea, th["tau"]))
    tailles = [math.exp(math.log(R4.TAILLE_FOCALE) + alea.gauss(0, th["heterogeneite"])) for _ in range(N)]
    bruit = [[alea.gauss(0, th["bruit"]) - th["bruit"] ** 2 / 2 for _ in range(N + 1)] for _ in range(R4.MOIS)]
    imite = [[(alea.random(), int(alea.random() * N), alea.random()) for _ in range(N)] for _ in range(R4.MOIS)]
    controle = next((m for m in range(R4.MOIS) if alea.random() < th["controle"]), None)
    return {"niveaux": niveaux, "tailles": tailles, "bruit": bruit, "imite": imite, "controle": controle}


def simuler(i: int, strategie: int, part_niveau2: float | None = None, severe: bool = False) -> dict:
    """Une arène : tirage i, l'agence de l'utilisateur joue `strategie` du premier au dernier mois."""
    th, h, cal = tirages()[i], _hasard(i, part_niveau2), calage()
    N = R4.AGENCES
    niveaux = list(h["niveaux"]) + [strategie]
    k = list(h["tailles"]) + [float(R4.TAILLE_FOCALE)]
    bascule_fin = [None] * (N + 1)   # mois où une agence de niveau 1 a fini de repasser à l'humain
    cumul = [0.0] * (N + 1)
    profit_par = [0.0] * (N + 1)
    part_ciblage = 0.5 if severe else 1.0
    pc = th["part_chat"]
    for m in range(R4.MOIS):
        controle = h["controle"] is not None and m >= h["controle"]
        n1 = sum(1 for a in range(N + 1) if niveaux[a] >= 1) / (N + 1)
        payes, revenus = [0.0] * (N + 1), [0.0] * (N + 1)
        for a in range(N + 1):
            lv = niveaux[a]
            fans = k[a] * R4.FANS_PAR_CREATRICE
            if lv == 0:
                cib = 1.0
            elif lv == 1:
                cib = cal["valeur"] * (1 - th["encombrement"] * n1)
            else:
                temoin = th["temoin"] * (2 if lv == 3 else 1)
                cib = (1 - temoin) * (1 + (cal["appris"] - 1) * fans / (fans + th["apprentissage"]))
            cib = 1 + part_ciblage * (cib - 1)
            ia = False
            if lv == 0:
                fr = 1 - th["transparence"] if controle else 1.0
            elif lv == 1:
                if not controle:
                    fr, ia = 1.0, True
                else:
                    if bascule_fin[a] is None:
                        bascule_fin[a] = m + th["bascule"]
                    if m < bascule_fin[a]:
                        fr, ia = 1 - th["divulgation"], True
                    else:
                        fr = 1 - th["transparence"]
            else:
                fr = 1 - th["transparence"]
            r = ((1 - pc) + pc * cib * fr) * math.exp(h["bruit"][m][a])
            if lv >= 2:
                cout = R4.COUT_HUMAIN - th["economie_ia"] / 2
            elif ia:
                cout = R4.COUT_HUMAIN - th["economie_ia"]
            else:
                cout = R4.COUT_HUMAIN
            prise = R4.PRISE[lv]
            marge = prise * (1 - R4.PLATEFORME) - cout
            revenus[a] = r
            payes[a] = (1 - prise) * (1 - R4.PLATEFORME) * r
            profit_par[a] = marge * r
            cumul[a] += k[a] * marge * r
        # Créatrices : départs, puis choix d'une agence par les partantes et les nouvelles.
        departs = [k[a] * min(0.5, th["depart"] * math.exp(th["sensibilite"] * (R4.PRISE[niveaux[a]] - 0.5)))
                   for a in range(N + 1)]
        total = sum(k)
        pool = sum(departs) + R4.CROISSANCE * total
        moy = sum(payes[a] * k[a] for a in range(N + 1)) / total if total > 0 else 1.0
        poids = []
        for a in range(N + 1):
            taille = k[a] - departs[a]
            if taille <= 0 and th["visibilite"] > 0:
                poids.append(0.0)
                continue
            poids.append(max(taille, 1e-9) ** th["visibilite"] * math.exp(th["attrait"] * (payes[a] / moy - 1)))
        sp = sum(poids)
        k = [max(0.0, k[a] - departs[a] + (pool * poids[a] / sp if sp > 0 else 0.0)) for a in range(N + 1)]
        # Imitation : les concurrents (jamais l'agence de l'utilisateur) comparent et copient.
        for a in range(N):
            u, j, u2 = h["imite"][m][a]
            if u >= th["imitation"] or j == a:
                continue
            if profit_par[j] > profit_par[a] and niveaux[j] != niveaux[a]:
                if niveaux[j] >= 2 and niveaux[a] < 2 and u2 >= th["capacite"]:
                    continue
                niveaux[a] = niveaux[j]
                if niveaux[a] == 1 and controle:
                    bascule_fin[a] = m  # déjà contrôlée : la nouvelle venue écrit en humain, à découvert
    rang = sum(1 for a in range(N) if cumul[a] < cumul[FOCALE]) / N
    mediane = sorted(cumul[:N])[N // 2]
    return {"rang": rang, "cumul": cumul[FOCALE], "mediane": mediane, "part": k[FOCALE] / sum(k),
            "niveau2": sum(1 for a in range(N) if niveaux[a] >= 2) / N, "controle": h["controle"]}


@lru_cache(maxsize=None)
def jouer(severe: bool = False) -> list[dict]:
    """Les 400 tirages, chacun rejoué pour les quatre stratégies."""
    out = []
    for i in range(R4.TIRAGES_ARENE):
        out.append({s: simuler(i, s, severe=severe) for s in R4.STRATEGIES})
    return out


@lru_cache(maxsize=None)
def imitateurs(part: float, severe: bool = False) -> list[dict]:
    """Les mêmes tirages, une part des concurrents au niveau 2 dès le départ ; stratégies 1 et 2."""
    return [{s: simuler(i, s, part_niveau2=part, severe=severe) for s in (1, 2)} for i in range(R4.TIRAGES_ARENE)]


@lru_cache(maxsize=None)
def affirmations(severe: bool = False) -> dict[str, dict]:
    """Les quatre affirmations Z du registre, et le test « quand les autres copient » des familles A et B."""
    j = jouer(severe)
    n = len(j)

    def devant(a, b):
        return sum(1 for t in j if t[a]["rang"] > t[b]["rang"]) / n

    out = {
        "Z01": {"part": devant(2, 1)}, "Z02": {"part": devant(2, 0)}, "Z03": {"part": devant(2, 3)},
    }
    moitie = imitateurs(0.5, severe)
    out["Z04"] = {"part": sum(1 for t in moitie if t[2]["cumul"] > t[2]["mediane"]) / n}
    for zid, enonce, seuil, _ in R4.Z:
        out[zid].update({"enonce": enonce, "seuil": seuil, "tient": out[zid]["part"] >= seuil})
    copie = {p: sum(1 for t in imitateurs(p, severe) if t[2]["cumul"] > t[1]["cumul"]) / n for p in R4.IMITATEURS}
    out["copie"] = {"parts": copie, "tient": all(v >= R4.SEUIL_ARENE for v in copie.values())}
    out["top1"] = {s: sum(1 for t in j if t[s]["rang"] >= 0.99) / n for s in R4.STRATEGIES}
    out["top10"] = {s: sum(1 for t in j if t[s]["rang"] >= 0.90) / n for s in R4.STRATEGIES}
    out["rang_median"] = {s: sorted(t[s]["rang"] for t in j)[n // 2] for s in R4.STRATEGIES}
    out["pire_rang"] = {s: min(t[s]["rang"] for t in j) for s in R4.STRATEGIES}
    return out


def sensibilite(param: str, a: int = 2, b: int = 1) -> list[tuple[float, float]]:
    """Pour un paramètre : la part des tirages où la stratégie a finit devant b, par cinquième du domaine."""
    j = jouer()
    th = tirages()
    lo, hi = R4.DOMAINE[param]
    out = []
    for q in range(5):
        x0, x1 = lo + (hi - lo) * q / 5, lo + (hi - lo) * (q + 1) / 5
        idx = [i for i in range(len(j)) if x0 <= th[i][param] <= x1]
        if idx:
            out.append(((x0 + x1) / 2, sum(1 for i in idx if j[i][a]["rang"] > j[i][b]["rang"]) / len(idx)))
    return out


def main() -> None:
    import time
    t0 = time.time()
    print("calage", calage())
    aff = affirmations()
    for k_, v in aff.items():
        print(k_, v)
    print("temps", round(time.time() - t0), "s")
    sev = affirmations(severe=True)
    print("variante sévère", {k_: (v.get("part"), v.get("tient")) for k_, v in sev.items() if k_.startswith("Z")},
          sev["copie"], sev["top1"])


if __name__ == "__main__":
    main()
