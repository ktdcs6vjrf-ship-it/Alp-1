"""La synthèse du cahier nº 4 : verdicts, batterie test par test, et ce qui survit.

Le verdict suit la règle des cahiers nº 1 à 3 (valeur q de Benjamini-Hochberg
sur la famille du nº 4 seule, sens annoncé, signe). La batterie ajoute, pour
chaque hypothèse, les tests de `registre4.TESTS` qui s'y appliquent ; chacun
rend « passe », « échoue » ou « sans objet ». Une hypothèse **survit** si son
verdict est « tient » et si elle passe tous les tests qui s'y appliquent. Rien
de cela n'est écrit à la main.
"""

from __future__ import annotations

from functools import lru_cache

from . import calcul4, stats, stress
from . import registre4 as R4
from .resultat import Resultat
from .synthese import SEUIL_Q

#: Les comparaisons qui forment un même « marché » pour le test des autres marchés.
FRERES = {
    "A01": ("A01", "A02", "A03"), "A02": ("A01", "A02", "A03"), "A03": ("A01", "A02", "A03"),
    "A04": ("A04", "A05", "A06"), "A05": ("A04", "A05", "A06"), "A06": ("A04", "A05", "A06"),
    "A07": ("A07", "A08", "A09"), "A08": ("A07", "A08", "A09"), "A09": ("A07", "A08", "A09"),
    "A10": ("A10", "A11", "A12"), "A11": ("A10", "A11", "A12"), "A12": ("A10", "A11", "A12"),
    "B01": ("B01", "B02", "B03"), "B02": ("B01", "B02", "B03"), "B03": ("B01", "B02", "B03"),
    "B04": ("B01", "B02", "B03"),
    "W01": ("W01", "W02", "W03"), "W02": ("W01", "W02", "W03"), "W03": ("W01", "W02", "W03"),
    "R01": ("R01", "R02", "R03"), "R02": ("R01", "R02", "R03"), "R03": ("R01", "R02", "R03"),
}


@lru_cache(maxsize=1)
def tous() -> dict[str, Resultat]:
    out: dict[str, Resultat] = calcul4.charger()["resultats"]
    ids = [h.id for h in R4.H]
    manquants, orphelins = set(ids) - set(out), set(out) - set(ids)
    if manquants or orphelins:
        raise KeyError(f"registre et résultats divergent : {manquants} {orphelins}")
    return {i: out[i] for i in ids}


@lru_cache(maxsize=1)
def batteries() -> dict[str, dict]:
    return calcul4.charger()["batteries"]


def arene_affirmations(severe: bool = False) -> dict:
    return calcul4.charger()["arene"]["severe" if severe else "affirmations"]


@lru_cache(maxsize=1)
def q_valeurs() -> dict[str, float]:
    res = tous()
    ids = list(res)
    return dict(zip(ids, stats.bh([max(res[i].p, 1e-300) for i in ids])))


@lru_cache(maxsize=1)
def holm() -> dict[str, float]:
    res = tous()
    ids = list(res)
    return dict(zip(ids, stress.holm([res[i].p for i in ids])))


def verdict(i: str) -> str:
    h = R4.par_id()[i]
    r = tous()[i]
    if q_valeurs()[i] >= SEUIL_Q:
        return "non établi"
    if h.sens == 0 or (r.effet > 0) == (h.sens > 0):
        return "tient"
    return "contraire"


def _sens(i: str) -> int:
    """Le sens annoncé, ou, pour une question ouverte, le signe observé."""
    h = R4.par_id()[i]
    if h.sens != 0:
        return h.sens
    return 1 if tous()[i].effet >= 0 else -1


def _dans_le_sens(i: str) -> bool:
    return (tous()[i].effet > 0) == (_sens(i) > 0)


def test(i: str, t: str) -> dict:
    """Un test de la batterie : {'etat': 'passe' | 'echoue' | 'sans objet', 'valeur': …, 'detail': …}."""
    if t not in R4.applicables(i):
        return {"etat": "sans objet", "valeur": None, "detail": ""}
    r, b, s = tous()[i], batteries().get(i, {}), _sens(i)

    def res(ok: bool, valeur, detail: str) -> dict:
        return {"etat": "passe" if ok else "echoue", "valeur": valeur, "detail": detail}

    if t == "nul":
        return res(r.p < 0.05 and _dans_le_sens(i), r.p, f"p = {r.p:.2g}")
    if t == "bh":
        return res(verdict(i) == "tient", q_valeurs()[i], f"q = {q_valeurs()[i]:.2g}")
    if t == "holm":
        return res(holm()[i] < 0.05 and _dans_le_sens(i), holm()[i], f"p de Holm = {holm()[i]:.2g}")
    if t == "t3":
        z = abs(stats.Phi_inv(max(r.p, 1e-300) / 2))
        return res(stress.passe_t3(r.effet, r.p, s, R4.SEUIL_T), z, f"|t| = {z:.2f}")
    if t == "coupes":
        part = stress.part_meme_sens(b["coupes"], s)
        return res(part >= R4.SEUIL_COUPES, part, f"{round(part * len(b['coupes']))} coupes sur {len(b['coupes'])}")
    if t == "marches":
        freres = FRERES[i]
        effets = [tous()[f].effet for f in freres]
        meme = sum(1 for e in effets if (e > 0) == (s > 0))
        return res(meme == len(effets), meme / len(effets), f"{meme} sur {len(effets)}")
    if t == "spec":
        sp = stress.resume_spec([e for e, _ in b["spec"]], [p for _, p in b["spec"]], s)
        ok = sp["meme_sens"] >= R4.SEUIL_SPEC_SENS and sp["signif"] >= R4.SEUIL_SPEC_SIGNIF
        return res(ok, sp, f"{sp['meme_sens'] * 100:.0f} % dans le sens, {sp['signif'] * 100:.0f} % significatifs "
                           f"({sp['n']} réglages)")
    if t == "cscv":
        c = b["cscv"]
        ok = c["perte"] <= R4.SEUIL_PERTE and c["pbo"] <= R4.SEUIL_PBO
        return res(ok, c, f"perte {c['perte'] * 100:.1f} %, PBO {c['pbo']:.2f}")
    if t == "spa":
        p = b["spa"]["p_spa"]
        return res(p < 0.05, p, f"p SPA = {p:.3f}")
    if t == "placebo":
        e, p = b["placebo"]
        return res(p >= 0.05, p, f"placebo {e:+.3f}, p = {p:.2f}")
    if t == "temps":
        serie = b["temps"] if "temps" in b else b["par_jour"]
        part = stress.part_meme_sens(serie, s)
        return res(part >= R4.SEUIL_TEMPS, part, f"{round(part * len(serie))} périodes sur {len(serie)}")
    if t == "dsr":
        d = b["dsr"]["dsr"]
        return res(d >= R4.SEUIL_DSR, d, f"DSR = {d:.2f} sur {b['dsr']['T']} périodes")
    if t == "arene":
        c = arene_affirmations()["copie"]
        parts = ", ".join(f"{v * 100:.0f} %" for v in c["parts"].values())
        return res(c["tient"], c["parts"], f"devant la mode : {parts} des tirages")
    raise KeyError(t)


@lru_cache(maxsize=None)
def bilan(i: str) -> dict:
    tests = {t: test(i, t) for t, _, _ in R4.TESTS}
    app = [t for t in tests if tests[t]["etat"] != "sans objet"]
    passes = [t for t in app if tests[t]["etat"] == "passe"]
    return {"tests": tests, "applicables": len(app), "passes": len(passes),
            "survit": verdict(i) == "tient" and len(passes) == len(app),
            "manque": [t for t in app if tests[t]["etat"] == "echoue"]}


def survivants() -> list[str]:
    return [i for i in tous() if bilan(i)["survit"]]


def comptes() -> dict[str, int]:
    v = [verdict(i) for i in tous()]
    return {"total": len(v), "tient": v.count("tient"), "contraire": v.count("contraire"), "non": v.count("non établi"),
            "survivent": len(survivants())}


def main() -> None:
    reg = R4.par_id()
    for i, r in tous().items():
        b = bilan(i)
        manque = ", ".join(b["manque"]) or "—"
        print(f"{i} {verdict(i):10s} q={q_valeurs()[i]:.3g} {b['passes']}/{b['applicables']} "
              f"{'SURVIT' if b['survit'] else '      '} manque : {manque:40s} {reg[i].enonce[:50]}")
    print(comptes())
    aff = arene_affirmations()
    for zid, *_ in R4.Z:
        print(zid, aff[zid])


if __name__ == "__main__":
    main()
