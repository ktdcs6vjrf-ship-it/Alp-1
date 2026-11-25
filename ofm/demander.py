"""Demander à un inconnu — Random Acts of Pizza.

Sur le forum Reddit « Random Acts of Pizza », un inconnu demande qu'on lui
offre une pizza ; un autre inconnu paie, ou non. C'est le geste le plus proche
du pourboire et de l'achat d'un contenu à quelqu'un qu'on ne connaît que par
écrit : un texte, un profil, un moment, et une décision de payer sans
contrepartie matérielle immédiate. 4 040 demandes, issue connue.

La mesure ajustée est un modèle linéaire de probabilité : toutes les variables
du registre ensemble, plus la tendance du forum (les dons se raréfient à
mesure que la communauté grandit), écarts-types robustes. Le coefficient se lit
directement en points de pourcentage, à toutes choses du registre égales.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from . import donnees, stats
from .resultat import Resultat, entier


def _motif(mots: list[str]) -> re.Pattern:
    return re.compile(r"\b(" + "|".join(re.escape(m) for m in mots) + r")\b")


#: Lexiques déclarés avec le registre, avant tout calcul. Ceux des récits
#: reprennent les familles d'Althoff et al. (2014), réduites à leurs mots
#: les moins ambigus.
LEXIQUES = {
    "D01": _motif(["thank", "thanks", "thank you", "appreciate", "appreciated",
                   "grateful", "gratitude"]),
    "D02": _motif(["pay it forward", "return the favor", "return the favour",
                   "pay you back", "pay back", "repay", "pay it back",
                   "reciprocate"]),
    "D03": re.compile(r"(imgur|\.jpe?g\b|\.png\b|\bproof\b)"),
    "D04": _motif(["job", "jobs", "unemployed", "unemployment", "fired",
                   "laid off", "interview", "paycheck", "hired"]),
    "D05": _motif(["rent", "bills", "bill", "broke", "bank", "overdraft",
                   "overdrawn", "money"]),
    "D06": _motif(["wife", "husband", "kids", "kid", "son", "daughter",
                   "family", "baby", "children"]),
    "D07": _motif(["college", "student", "students", "finals", "semester",
                   "exam", "exams", "dorm", "university"]),
    "D08": _motif(["craving", "crave", "birthday", "party", "drunk",
                   "celebrate", "celebrating"]),
    "D13": _motif(["please"]),
    "D14": _motif(["tonight", "today", "asap", "right now"]),
}

NY_STD, NY_DST = timedelta(hours=-5), timedelta(hours=-4)


def _dimanche(an: int, mois: int, rang: int) -> datetime:
    d = datetime(an, mois, 1)
    d += timedelta(days=(6 - d.weekday()) % 7)
    return d + timedelta(weeks=rang - 1)


def new_york(ts: float) -> datetime:
    """Heure de New York, règle d'heure d'été américaine de 2007."""
    u = datetime.fromtimestamp(ts, timezone.utc).replace(tzinfo=None)
    debut = _dimanche(u.year, 3, 2) + timedelta(hours=7)    # 2 h locales, en UTC
    fin = _dimanche(u.year, 11, 1) + timedelta(hours=6)
    return u + (NY_DST if debut <= u < fin else NY_STD)


def _mots(texte: str) -> int:
    return len(re.findall(r"[a-z']+", texte))


@lru_cache(maxsize=1)
def table() -> tuple[dict, ...]:
    """Une ligne par demande : issue, variables du registre, contrôles."""
    lignes = []
    t0 = min(r["unix_timestamp_of_request_utc"] for r in donnees.raop())
    for r in donnees.raop():
        texte = (r["request_title"] + " \n " + r["request_text_edit_aware"]).lower()
        corps = r["request_text_edit_aware"].lower()
        ny = new_york(r["unix_timestamp_of_request_utc"])
        f = {k: (1.0 if m.search(texte) else 0.0) for k, m in LEXIQUES.items()}
        lignes.append({
            "y": 1.0 if r["requester_received_pizza"] else 0.0,
            **f,
            "mots": _mots(corps),
            "karma": r["requester_upvotes_minus_downvotes_at_request"],
            "age": r["requester_account_age_in_days_at_request"],
            "membre": 1.0 if (r["requester_number_of_comments_in_raop_at_request"] > 0
                              or r["requester_number_of_posts_on_raop_at_request"] > 0) else 0.0,
            "jour": ny.day, "semaine": ny.weekday(), "heure": ny.hour,
            "ans": (r["unix_timestamp_of_request_utc"] - t0) / (365.25 * 86400),
        })
    med = {k: stats.quantile([l[k] for l in lignes], 0.5) for k in ("mots", "karma", "age")}
    for l in lignes:
        l["D09"] = 1.0 if l["mots"] > med["mots"] else 0.0
        l["D10"] = 1.0 if l["karma"] > med["karma"] else 0.0
        l["D11"] = 1.0 if l["age"] > med["age"] else 0.0
        l["D12"] = l["membre"]
        l["D15"] = 1.0 if l["jour"] <= 10 else 0.0
        l["D16"] = 1.0 if l["semaine"] >= 5 else 0.0
        l["D17"] = 1.0 if l["heure"] >= 18 else 0.0
    return tuple(lignes)


IDS = tuple(f"D{k:02d}" for k in range(1, 18))


@lru_cache(maxsize=1)
def modele() -> stats.Ajustement:
    lignes = table()
    noms = ["const", *IDS, "ans"]
    X = [[1.0, *[l[i] for i in IDS], l["ans"]] for l in lignes]
    return stats.mco(X, [l["y"] for l in lignes], noms)


def _pct(v: float, nd: int = 1) -> str:
    return f"{v * 100:.{nd}f}".replace(".", ",") + " %"


@lru_cache(maxsize=1)
def resultats() -> dict[str, Resultat]:
    lignes = table()
    fit = modele()
    out = {}
    for i in IDS:
        avec = [l["y"] for l in lignes if l[i] == 1.0]
        sans = [l["y"] for l in lignes if l[i] == 0.0]
        brut = stats.deux_proportions(int(sum(avec)), len(avec), int(sum(sans)), len(sans))
        lo, hi = fit.ic(i)
        out[i] = Resultat(
            id=i, effet=fit.b(i) * 100, ic=(lo * 100, hi * 100), p=fit.p(i),
            n=len(lignes), unite="pt",
            lecture=(f"{_pct(brut.a)} avec, {_pct(brut.b)} sans "
                     f"({entier(len(avec))} demandes contre {entier(len(sans))})"),
            methode="probabilité linéaire ajustée sur les 17 variables et la tendance, robuste",
            base=brut.b, relatif=(fit.b(i) / brut.b if brut.b else None),
            extra={"taux_avec": brut.a, "taux_sans": brut.b, "n_avec": len(avec),
                   "n_sans": len(sans)},
        )
    return out


def taux_par(cle: str, valeurs) -> list[tuple[int, float, int, float]]:
    """(valeur, taux, effectif, demi-largeur à 95 %) pour une variable entière."""
    lignes = table()
    out = []
    for v in valeurs:
        ys = [l["y"] for l in lignes if l[cle] == v]
        if not ys:
            continue
        p = sum(ys) / len(ys)
        out.append((v, p, len(ys), 1.96 * math.sqrt(p * (1 - p) / len(ys))))
    return out


def hors_bande() -> dict:
    """Points du profil jour × heure qui sortent de la bande à 95 % de la loi nulle."""
    b = base_globale()
    out = {"jours": 0, "heures": 0, "total": 0}
    for cle, vals, nom in (("jour", range(1, 32), "jours"), ("heure", range(24), "heures")):
        for v, t, n, _ in taux_par(cle, vals):
            out["total"] += 1
            if abs(t - b) > 1.96 * math.sqrt(b * (1 - b) / n):
                out[nom] += 1
    out["dehors"] = out["jours"] + out["heures"]
    out["attendus"] = 0.05 * out["total"]
    return out


def nuit() -> dict:
    """Constat a posteriori, hors registre : demandes de 0 h à 6 h contre le reste."""
    lignes = table()
    a = [l["y"] for l in lignes if l["heure"] < 6]
    b = [l["y"] for l in lignes if l["heure"] >= 6]
    e = stats.deux_proportions(int(sum(a)), len(a), int(sum(b)), len(b))
    return {"a": e.a, "b": e.b, "n": len(a), "p": e.p}


def base_globale() -> float:
    lignes = table()
    return sum(l["y"] for l in lignes) / len(lignes)


@lru_cache(maxsize=1)
def grille_statut_effort(k: int = 5) -> tuple[list[list[float]], list[float], list[float]]:
    """Taux de réussite par quintile de karma (lignes) et de longueur (colonnes)."""
    lignes = table()
    qk = [stats.quantile([l["karma"] for l in lignes], (i + 1) / k) for i in range(k - 1)]
    qm = [stats.quantile([l["mots"] for l in lignes], (i + 1) / k) for i in range(k - 1)]

    def rang(v, bornes):
        return sum(1 for b in bornes if v > b)

    s = [[0.0] * k for _ in range(k)]
    n = [[0] * k for _ in range(k)]
    for l in lignes:
        a, b = rang(l["karma"], qk), rang(l["mots"], qm)
        s[a][b] += l["y"]
        n[a][b] += 1
    return ([[s[a][b] / n[a][b] if n[a][b] else 0.0 for b in range(k)] for a in range(k)],
            qk, qm)


def main() -> None:
    from .registre import par_id
    reg = par_id()
    for i, r in resultats().items():
        print(f"{i} {reg[i].enonce[:58]:58s} {r.effet:+6.2f} pt "
              f"[{r.ic[0]:+.2f}, {r.ic[1]:+.2f}] p={r.p:.4f}  {r.lecture}")
    print("base", base_globale(), "tendance/an", modele().b("ans"))


if __name__ == "__main__":
    main()
