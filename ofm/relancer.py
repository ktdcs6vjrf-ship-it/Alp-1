"""Relancer — trois messages groupés tirés au sort.

Hillstrom (2008) : 64 000 clients d'un vendeur en ligne reçoivent, **tirés au
sort**, un courriel « hommes », un courriel « femmes » ou rien ; on suit deux
semaines de visites, d'achats et de dépenses. Lenta (2020) : 687 029 clients
d'une enseigne reçoivent ou non un SMS, tiré au sort trois fois sur quatre ;
on suit la visite en magasin. X5 RetailHero (2019) : 200 039 clients, un SMS
tiré au sort une fois sur deux, l'achat ensuite, et l'historique d'achats
d'avant le message.

C'est la question la plus fréquente d'une agence : un message envoyé à tous
fait-il acheter, et sur qui agit-il ? Le tirage au sort fait la loi nulle —
l'effet est causal par construction, et l'écart d'effet entre deux groupes de
clients aussi, puisque le tirage a lieu dans chacun.
"""

from __future__ import annotations

import math
from functools import lru_cache

from . import donnees2, stats
from .offrir import _dol, _pct
from .resultat import Resultat, entier


def _traite(r) -> int:
    return 0 if r["courriel"] == "0" else 1


def prop(rid: str, a: list[int], b: list[int], quoi: str) -> Resultat:
    """a : issues (0/1) des traités, b : des témoins."""
    e = stats.deux_proportions(sum(a), len(a), sum(b), len(b))
    lo, hi = e.ic()
    return Resultat(
        id=rid, effet=e.diff * 100, ic=(lo * 100, hi * 100), p=e.p, n=len(a) + len(b),
        unite="pt", lecture=f"{_pct(e.a)} contre {_pct(e.b)} ({quoi})",
        methode="écart de proportions, tirage au sort", base=e.b, relatif=e.relatif,
        extra={"a": e.a, "b": e.b, "na": len(a), "nb": len(b)},
    )


def interaction(rid: str, rows, t, y, g, quoi: str, ailleurs: str = "ailleurs") -> Resultat:
    """Écart d'effet du message entre deux groupes de clients (g = 1 contre 0).

    Probabilité linéaire y ~ 1 + t + g + t·g, écart-type robuste : le
    coefficient de t·g est la différence des deux effets, en points."""
    rows = [r for r in rows if g(r) is not None]
    X = [[1.0, float(t(r)), float(g(r)), float(t(r) * g(r))] for r in rows]
    fit = stats.mco(X, [float(y(r)) for r in rows], ["c", "t", "g", "tg"])
    lo, hi = fit.ic("tg")

    def eff(gv):
        sub = [r for r in rows if g(r) == gv]
        a = [y(r) for r in sub if t(r) == 1]
        b = [y(r) for r in sub if t(r) == 0]
        return sum(a) / len(a) - sum(b) / len(b), len(sub)

    e1, n1 = eff(1)
    e0, n0 = eff(0)
    return Resultat(
        id=rid, effet=fit.b("tg") * 100, ic=(lo * 100, hi * 100), p=fit.p("tg"), n=len(rows),
        unite="pt",
        lecture=(f"effet du message {e1 * 100:+.2f} pt {quoi} ({entier(n1)} clients), "
                 f"{e0 * 100:+.2f} pt {ailleurs} ({entier(n0)})").replace(".", ","),
        methode="interaction en probabilité linéaire, robuste",
        extra={"e1": e1, "e0": e0, "n1": n1, "n0": n0},
    )


def _assorti(rows) -> Resultat:
    """E04 : le courriel de la catégorie déjà achetée, contre l'autre.

    Chez les clients d'une seule catégorie, le type de courriel est tiré au
    sort : l'écart est causal dans chaque catégorie, puis moyenné au poids de
    la catégorie (le courriel « hommes » marche mieux partout, et c'est
    précisément ce que la moyenne par catégorie neutralise)."""
    strates = {"hommes": [r for r in rows if r["hommes"] == 1 and r["femmes"] == 0],
               "femmes": [r for r in rows if r["hommes"] == 0 and r["femmes"] == 1]}
    bon = {"hommes": "h", "femmes": "f"}
    total = sum(len([r for r in s if r["courriel"] != "0"]) for s in strates.values())
    d = v = 0.0
    parts, base_n, base_x = {}, 0, 0
    for nom, sub in strates.items():
        a = [r["visite"] for r in sub if r["courriel"] == bon[nom]]
        b = [r["visite"] for r in sub if r["courriel"] not in ("0", bon[nom])]
        e = stats.deux_proportions(sum(a), len(a), sum(b), len(b))
        w = (len(a) + len(b)) / total
        d += w * e.diff
        v += w * w * e.se ** 2
        parts[nom] = (e.a, e.b)
        base_x += sum(b)
        base_n += len(b)
    se = math.sqrt(v)
    base = base_x / base_n
    return Resultat(
        id="E04", effet=d * 100, ic=((d - 1.96 * se) * 100, (d + 1.96 * se) * 100),
        p=stats.p_bilateral(d / se), n=total, unite="pt",
        lecture=(f"clients « hommes » : {_pct(parts['hommes'][0])} de visites avec le courriel hommes, "
                 f"{_pct(parts['hommes'][1])} avec l'autre ; clients « femmes » : "
                 f"{_pct(parts['femmes'][0])} contre {_pct(parts['femmes'][1])}"),
        methode="écart de proportions par catégorie, tirage au sort, moyenne pondérée",
        base=base, relatif=d / base, extra={"parts": parts},
    )


def _mediane(vals) -> float:
    return stats.quantile([v for v in vals if v is not None], 0.5)


@lru_cache(maxsize=1)
def resultats() -> dict[str, Resultat]:
    out: dict[str, Resultat] = {}
    # --- Hillstrom ---------------------------------------------------------
    hs = donnees2.hillstrom()
    t1 = [r for r in hs if _traite(r)]
    t0 = [r for r in hs if not _traite(r)]
    out["E01"] = prop("E01", [r["achat"] for r in t1], [r["achat"] for r in t0], "courriel contre aucun")
    a, b = [r["depense"] for r in t1], [r["depense"] for r in t0]
    e = stats.deux_moyennes(a, b)
    lo, hi = e.ic()
    out["E02"] = Resultat(
        id="E02", effet=e.diff, ic=(lo, hi), p=e.p, n=len(a) + len(b), unite="$",
        lecture=f"{_dol(e.a)} contre {_dol(e.b)} dépensés par client en deux semaines",
        # Pas de budget « taux » : une dépense se budgète sur sa variance (`budgets_hillstrom`).
        methode="écart de moyennes (Welch), tirage au sort", base=None, relatif=None,
        extra={"a": e.a, "b": e.b, "sd_a": math.sqrt(stats.variance(a)), "sd_b": math.sqrt(stats.variance(b))},
    )
    out["E03"] = prop("E03", [r["visite"] for r in t1], [r["visite"] for r in t0], "courriel contre aucun")
    out["E04"] = _assorti(hs)
    med_rec = _mediane(r["recence"] for r in hs)
    med_hist = _mediane(r["historique"] for r in hs)
    out["E05"] = interaction("E05", hs, _traite, lambda r: r["visite"],
                             lambda r: 1 if r["recence"] <= med_rec else 0,
                             f"chez les clients récents (dernier achat à {med_rec:.0f} mois ou moins)",
                             "chez les plus anciens")
    out["E06"] = interaction("E06", hs, _traite, lambda r: r["visite"],
                             lambda r: 1 if r["historique"] > med_hist else 0,
                             "chez les plus gros clients", "chez les autres")
    out["E07"] = interaction("E07", hs, _traite, lambda r: r["visite"],
                             lambda r: r["nouveau"], "chez les clients arrivés dans l'année",
                             "chez les plus anciens")
    # --- Lenta ---------------------------------------------------------------
    le = donnees2.lenta()
    out["E08"] = prop("E08", [r["y"] for r in le if r["t"] == 1], [r["y"] for r in le if r["t"] == 0],
                      "SMS contre témoin")
    out["E09"] = interaction("E09", le, lambda r: r["t"], lambda r: r["y"],
                             lambda r: None if r["rep_sms"] is None else (1 if r["rep_sms"] > 0 else 0),
                             "chez qui a déjà répondu à un SMS", "chez qui n'a jamais répondu")
    med_rc = _mediane(r["recus_3m"] for r in le)
    out["E10"] = interaction("E10", le, lambda r: r["t"], lambda r: r["y"],
                             lambda r: None if r["recus_3m"] is None else (1 if r["recus_3m"] >= med_rc else 0),
                             "chez les clients fréquents", "chez les autres")
    med_pr = _mediane(r["promo"] for r in le)
    out["E11"] = interaction("E11", le, lambda r: r["t"], lambda r: r["y"],
                             lambda r: None if r["promo"] is None else (1 if r["promo"] > med_pr else 0),
                             "chez les chasseurs de promotions", "chez les autres")
    hom = [r for r in le if r["sexe"] == "m"]
    out["E12"] = prop("E12", [r["y"] for r in hom if r["t"] == 1], [r["y"] for r in hom if r["t"] == 0],
                      "hommes, SMS contre témoin")
    # --- X5 ------------------------------------------------------------------
    x5 = donnees2.x5()
    out["E13"] = prop("E13", [r["y"] for r in x5 if r["t"] == 1], [r["y"] for r in x5 if r["t"] == 0],
                      "SMS contre témoin")
    med_r = _mediane(r["recence_j"] for r in x5)
    out["E14"] = interaction("E14", x5, lambda r: r["t"], lambda r: r["y"],
                             lambda r: None if r["recence_j"] is None else (1 if r["recence_j"] <= med_r else 0),
                             f"chez les clients récents (dernier passage à {med_r:.0f} jours ou moins)",
                             "chez les autres")
    med_p = _mediane(r["passages"] for r in x5)
    out["E15"] = interaction("E15", x5, lambda r: r["t"], lambda r: r["y"],
                             lambda r: 1 if r["passages"] >= med_p else 0,
                             f"chez les clients fréquents ({med_p:.0f} passages ou plus)", "chez les autres")
    out["E16"] = interaction("E16", x5, lambda r: r["t"], lambda r: r["y"],
                             lambda r: 1 if (r["express"] or 0) >= 1 else 0,
                             "chez les clients des promotions", "chez les autres")
    return out


@lru_cache(maxsize=1)
def bras_hillstrom() -> list[tuple[str, float, float, float, int]]:
    """Visite, achat et dépense par bras du courriel : (nom, visite, achat, dépense, n)."""
    out = []
    for code, nom in (("0", "aucun"), ("f", "femmes"), ("h", "hommes")):
        sub = [r for r in donnees2.hillstrom() if r["courriel"] == code]
        n = len(sub)
        out.append((nom, sum(r["visite"] for r in sub) / n, sum(r["achat"] for r in sub) / n,
                    sum(r["depense"] for r in sub) / n, n))
    return out


def grille_hillstrom(y: str = "visite") -> tuple[list[list[float]], list[str], list[str]]:
    """Effet du courriel (pt) par récence (lignes) et dépense de l'année (colonnes)."""
    hs = donnees2.hillstrom()
    rec = [(1, 2, "1–2 mois"), (3, 5, "3–5"), (6, 8, "6–8"), (9, 12, "9–12")]
    q = [stats.quantile([r["historique"] for r in hs], k / 3) for k in (1, 2)]
    hist = [(-1, q[0], "petit"), (q[0], q[1], "moyen"), (q[1], 1e12, "gros")]
    z = []
    for lo, hi, _ in rec:
        ligne = []
        for a, b, _ in hist:
            sub = [r for r in hs if lo <= r["recence"] <= hi and a < r["historique"] <= b]
            t1 = [r[y] for r in sub if _traite(r)]
            t0 = [r[y] for r in sub if not _traite(r)]
            ligne.append((sum(t1) / len(t1) - sum(t0) / len(t0)) * 100)
        z.append(ligne)
    return z, [x[2] for x in rec], [x[2] for x in hist]


def budgets_hillstrom() -> tuple[float, float]:
    """Envois par version pour revérifier, sur le même courriel, la hausse d'achats
    et la hausse de dépense, chacune planifiée à la moitié de sa taille.

    L'achat se budgète comme deux taux (à sa propre base) ; la dépense sur sa
    variance réelle, presque toute faite de zéros et de rares gros paniers.
    C'est l'argument de Lewis et Rao (2015), chiffré sur ce marché."""
    from .synthese import TRANSPOSITION
    R = resultats()
    a = R["E01"].extra
    n_achat = stats.n_par_bras(a["b"], (a["a"] / a["b"] - 1) * TRANSPOSITION)
    e = R["E02"].extra
    za, zb = stats.Phi_inv(0.975), stats.Phi_inv(0.80)
    delta = (e["a"] - e["b"]) * TRANSPOSITION
    n_dep = (za + zb) ** 2 * (e["sd_a"] ** 2 + e["sd_b"] ** 2) / delta ** 2
    return n_achat, n_dep


def _effet(sub) -> tuple[float, float, int]:
    a = [r["y"] for r in sub if r["t"] == 1]
    b = [r["y"] for r in sub if r["t"] == 0]
    e = stats.deux_proportions(sum(a), len(a), sum(b), len(b))
    return e.diff * 100, 1.96 * e.se * 100, len(sub)


def lenta_par_reponse() -> list[tuple[str, float, float, int]]:
    """Effet du SMS (pt de visites) selon la part de réponses aux SMS passés."""
    bornes = [(None, None, "jamais"), (0.0, 0.25, "≤ 25 %"), (0.25, 0.5, "25–50 %"),
              (0.5, 0.75, "50–75 %"), (0.75, 1.01, "> 75 %")]
    out = []
    le = [r for r in donnees2.lenta() if r["rep_sms"] is not None]
    for lo, hi, nom in bornes:
        if lo is None:
            sub = [r for r in le if r["rep_sms"] == 0]
        else:
            sub = [r for r in le if lo < r["rep_sms"] <= hi] if lo > 0 else \
                  [r for r in le if 0 < r["rep_sms"] <= hi]
        e, h, n = _effet(sub)
        out.append((nom, e, h, n))
    return out


def grille_x5() -> tuple[list[list[float]], list[str], list[str]]:
    """Effet du SMS (pt d'achats) par récence (lignes) et passages en caisse (colonnes)."""
    x5 = [r for r in donnees2.x5() if r["recence_j"] is not None]
    qr = [stats.quantile([r["recence_j"] for r in x5], k / 3) for k in (1, 2)]
    qp = [stats.quantile([r["passages"] for r in x5], k / 3) for k in (1, 2)]
    rec = [(-1, qr[0], "récents"), (qr[0], qr[1], "entre deux"), (qr[1], 1e9, "endormis")]
    pas = [(-1, qp[0], "rares"), (qp[0], qp[1], "moyens"), (qp[1], 1e9, "fréquents")]
    z = []
    for a, b, _ in rec:
        z.append([_effet([r for r in x5 if a < r["recence_j"] <= b and c < r["passages"] <= d])[0]
                  for c, d, _ in pas])
    return z, [x[2] for x in rec], [x[2] for x in pas]


def main() -> None:
    from .registre2 import par_id
    reg = par_id()
    for i, r in resultats().items():
        print(f"{i} {reg[i].enonce[:58]:58s} {r.effet:+8.3f} {r.unite:3s} "
              f"[{r.ic[0]:+.3f}, {r.ic[1]:+.3f}] p={r.p:.2e}  {r.lecture}")
    print(bras_hillstrom())


if __name__ == "__main__":
    main()
