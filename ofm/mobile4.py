"""La version mobile du cahier nº 4, dans la direction artistique de Lueur.

Même page que les cahiers nº 1 à 3 : feuille de style, dock, recherche et script
repris du gabarit du nº 1 à la construction (`mobile3.commun`, clés de lecture
`ofm-cahier4-*`). On modifie `docs/ofm/cahier-4-mobile.template.html`, puis
`python -m ofm.mobile4`. La commande écrit aussi `docs/ofm/cahier-4-valeurs.json` :
valeurs, verdicts, survie à la batterie, plan et formation, que l'app Lueur
pourra lire sans rien recopier.
"""

from __future__ import annotations

import html as H
import json
import re
from functools import lru_cache
from pathlib import Path

from alp1.figterm import _num

from . import (calcul4, clair4, donnees, donnees2, donnees3, donnees4, equilibre4, formation4, litterature4, mobile,
               synthese4)
from . import registre4 as R4
from .etalonnage4 import lire as etalonnage
from .figmobile4 import COURT, rendre
from .mobile import (MOTS_MINUTE, PILULE, TEMPLATE as GABARIT_1, _attr, _e, _effet, _mini, _mots_lus,
                     _phrase_verdicts, _trois, _typo, icone, pied)
from .resultat import entier

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "docs" / "ofm" / "cahier-4-mobile.template.html"
OUTPUT = ROOT / "docs" / "ofm" / "cahier-4-mobile.html"
VALEURS = ROOT / "docs" / "ofm" / "cahier-4-valeurs.json"

# Pictogrammes de Lucide (licence ISC) pour les sujets propres au nº 4.
for _cle, _svg in {
    "shield-check": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
    "store": '<path d="m2 7 4.41-4.41A2 2 0 0 1 7.83 2h8.34a2 2 0 0 1 1.42.59L22 7"/><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><path d="M15 22v-4a2 2 0 0 0-2-2h-2a2 2 0 0 0-2 2v4"/><path d="M2 7h20"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    "shuffle": '<path d="m18 14 4 4-4 4"/><path d="m18 2 4 4-4 4"/><path d="M2 18h1.973a4 4 0 0 0 3.3-1.7l5.454-8.6a4 4 0 0 1 3.3-1.7H22"/><path d="M2 6h1.972a4 4 0 0 1 3.6 2.2"/><path d="M22 18h-6.041a4 4 0 0 1-3.3-1.8l-.359-.45"/>',
    "flag": '<path d="M4 22V4a1 1 0 0 1 .4-.8A6 6 0 0 1 8 2c3 0 5 2 7.333 2q2 0 3.067-.8A1 1 0 0 1 20 4v10a1 1 0 0 1-.4.8A6 6 0 0 1 16 16c-3 0-5-2-8-2a6 6 0 0 0-4 1.528"/>',
    "fish": '<path d="M6.5 12c.94-3.46 4.94-6 8.5-6 3.56 0 6.06 2.54 7 6-.94 3.47-3.44 6-7 6s-7.56-2.53-8.5-6Z"/><path d="M18 12v.5"/><path d="M7 10.67C7 8 5.58 5.97 2.73 5.5c-1.17 1.95-.94 4.43.37 6.5-1.31 2.07-1.54 4.55-.37 6.5C5.58 18.03 7 16 7 13.33"/>',
    "zap": '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/>',
    "swords": '<polyline points="14.5 17.5 3 6 3 3 6 3 17.5 14.5"/><line x1="13" x2="19" y1="19" y2="13"/><line x1="16" x2="20" y1="16" y2="20"/><line x1="19" x2="21" y1="21" y2="19"/><polyline points="14.5 6.5 18 3 21 3 21 6 17.5 9.5"/><line x1="5" x2="9" y1="14" y2="18"/><line x1="7" x2="4" y1="17" y2="20"/><line x1="3" x2="5" y1="19" y2="21"/>',
    "map": '<path d="M14.106 5.553a2 2 0 0 0 1.788 0l3.659-1.83A1 1 0 0 1 21 4.619v12.764a1 1 0 0 1-.553.894l-4.553 2.277a2 2 0 0 1-1.788 0l-4.212-2.106a2 2 0 0 0-1.788 0l-3.659 1.83A1 1 0 0 1 3 19.381V6.618a1 1 0 0 1 .553-.894l4.553-2.277a2 2 0 0 1 1.788 0z"/><path d="M15 5.764v15"/><path d="M9 3.236v15"/>',
    "graduation-cap": '<path d="M21.42 10.922a1 1 0 0 0-.019-1.838L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.832l8.57 3.908a2 2 0 0 0 1.66 0z"/><path d="M22 10v6"/><path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5"/>',
    "scale": '<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>',
}.items():
    mobile.ICONES.setdefault(_cle, _svg)

GROUPES = (
    ("Pour commencer", ("resume", "methode")),
    ("Le marché et la concurrence", ("marche", "niveaux")),
    ("Les tests", ("apprendre", "bandit", "foule", "baleines", "acceleration")),
    ("Quand tout le monde s'adapte", ("arene",)),
    ("Passer à l'action", ("plan", "formation")),
    ("À savoir aussi", ("faux", "regles", "ailleurs")),
    ("Annexes", ("registre", "sources")),
)

SUJETS = {
    "resume": ("L'essentiel", "Ce qu'il faut retenir du cahier", "sparkles"),
    "methode": ("La batterie", "Treize tests pour ne pas se tromper", "shield-check"),
    "marche": ("Le marché", "Où va l'argent des fans ?", "store"),
    "niveaux": ("La concurrence", "Combien de coups d'avance ?", "users"),
    "apprendre": ("Apprendre chez soi", "À qui écrire d'abord ?", "target"),
    "bandit": ("Le bandit", "Pousser ce qui marche ?", "shuffle"),
    "foule": ("La foule", "Fuir la foule, être premier ?", "flag"),
    "baleines": ("Les baleines", "Les gros fans restent-ils gros ?", "fish"),
    "acceleration": ("L'accélération", "L'avance qui passe tout", "zap"),
    "arene": ("L'arène", "Et quand les autres copient ?", "swords"),
    "plan": ("Le plan de A à Z", "Huit étapes, chacune prouvée", "map"),
    "formation": ("La formation", "{n_lecons} leçons, simplement", "graduation-cap"),
    "faux": ("Ne tient pas", "Ce que les données ne montrent pas", "ban"),
    "regles": ("Les garde-fous", "Ce qui ne se négocie pas", "scale"),
    "ailleurs": ("Ailleurs", "Ce que d'autres études ont établi", "globe"),
    "registre": ("Les {n_hyp} idées", "Toutes, avec leur verdict", "list-checks"),
    "sources": ("Sources", "D'où viennent les chiffres", "book-marked"),
}

#: Les sections qui portent des cartes, pour la barre de verdicts des tuiles.
FAMILLES_SECTION = {"apprendre": "A", "bandit": "B", "foule": "K", "baleines": "W", "acceleration": "R"}
NOM_TEST = {t: nom for t, nom, _ in R4.TESTS}


def _s(v: float, nd: int = 2) -> str:
    return ("+" if v >= 0 else "−") + _num(abs(v), nd)


def _pc(v: float, nd: int = 0) -> str:
    return _num(v * 100, nd) + " %"


@lru_cache(maxsize=1)
def valeurs() -> dict[str, str]:
    C = calcul4.charger()
    R, c = synthese4.tous(), synthese4.comptes()
    aff = C["arene"]["affirmations"]
    v: dict[str, str] = {
        "n_hyp": str(c["total"]), "n_tient": str(c["tient"]), "n_contraire": str(c["contraire"]),
        "n_non": str(c["non"]), "n_survivent": str(c["survivent"]), "n_tests": str(len(R4.TESTS)),
        "n_arenes": entier(R4.TIRAGES_ARENE), "n_agences": str(R4.AGENCES),
        "n_lecons": str(sum(1 for _ in formation4.lecons())),
    }
    b = synthese4.bilan("R03")
    v.update({"r03_passes": str(b["passes"]), "r03_app": str(b["applicables"])})
    G = C["gains"]
    for jeu, k in (("x5", "x5"), ("hillstrom", "hi"), ("lenta", "le")):
        for r in ("appris", "valeur", "risque", "hasard"):
            v[f"{k}_{r}"] = _s(G[jeu][r], 2)
    v["a12_effet"] = _s(R["A12"].effet, 2)
    v["b04_effet"] = _s(R["B04"].effet, 3)
    v["b04_d"] = v["b04_effet"]
    for i in ("R01", "R02", "R03"):
        v[f"{i.lower()}_ic"] = _s(R[i].effet, 3)
    copie = aff["copie"]["parts"]
    v.update({"copie_10": _pc(copie[0.1]), "copie_50": _pc(copie[0.5]), "copie_90": _pc(copie[0.9]),
              "arene_21": _pc(aff["Z01"]["part"]), "arene_20": _pc(aff["Z02"]["part"]),
              "arene_23": _pc(aff["Z03"]["part"]), "arene_z04": _pc(aff["Z04"]["part"]),
              "top1_max": _pc(max(aff["top1"].values())),
              "rang_med_0": _pc(aff["rang_median"][0]), "rang_med_1": _pc(aff["rang_median"][1]),
              "rang_med_2": _pc(aff["rang_median"][2]), "rang_med_3": _pc(aff["rang_median"][3]),
              "rho_appris": _num(C["arene"]["calage"]["appris"], 2), "rho_valeur": _num(C["arene"]["calage"]["valeur"], 2)})
    eq = equilibre4.equilibre("lenta")
    v.update({"lenta_z_rep": _num(eq["rep_sms"][1], 0), "lenta_z_sexe": _num(eq["sexe_f"][1], 0)})
    v["w01_deja"] = _pc(1 - C["baleines"]["cdnow"][str(R4.BALEINE)]["part"])
    k3, k3p = C["k03"], C["k03_placebo"]
    v.update({"k03_d": _s(k3["d"], 1), "k03_placebo": _s(k3p["d"], 1)})
    ch = litterature4.CHIFFRES
    v.update({"tau": _num(ch["tau"], 1), "divulgation": _pc(ch["divulgation"], 1),
              "obp_th": _pc(ch["obp_thompson"], 2), "obp_ha": _pc(ch["obp_hasard"], 2),
              "brut": _num(ch["brut_2024"] / 1e9, 2) + " milliards de dollars",
              "croiss_brut": _pc(ch["croissance_brut"]), "croiss_crea": _pc(ch["croissance_createurs"]),
              "fans_par": _num(ch["fans_2024"] / ch["createurs_2024"], 0),
              "par_creatrice": entier(ch["brut_2024"] / ch["createurs_2024"]) + " $"})
    e = etalonnage()
    v.update({"etal_a_nul": _num(e["a_nul"]["conclut"] * 100, 1), "etal_couv": _num(e["a_heterogene"]["couverture"] * 100, 0),
              "etal_spa": _pc(e["spa_nul"]["spa"], 1), "etal_holm": _pc(e["holm"]["holm"], 1),
              "etal_holm_brut": _pc(e["holm"]["sans_correction"]), "etal_dsr": _pc(e["dsr"]["dsr"], 1)})
    v["n_refs"] = str(len(litterature4.REFS))
    return v


# ---------------------------------------------------------------------------
# Les blocs de la page
# ---------------------------------------------------------------------------

def _ids(a: str, b: str) -> list[str]:
    ordre = [h.id for h in R4.H]
    return ordre[ordre.index(a):ordre.index(b) + 1]


def _bat_ligne(i: str) -> str:
    b = synthese4.bilan(i)
    if b["survit"]:
        return f'<p class="res-ofm"><b>Batterie :</b> passe les {b["applicables"]} tests qui s’appliquent.</p>'
    manque = ", ".join(NOM_TEST[t].lower() for t in b["manque"])
    return (f'<p class="res-ofm"><b>Batterie :</b> {b["passes"]} tests sur {b["applicables"]} ; '
            f'échoue : {_e(manque)}.</p>')


def cartes(ids: list[str]) -> str:
    R, reg = synthese4.tous(), R4.par_id()
    lo = min(min(R[i].ic[0], 0.0) for i in ids)
    hi = max(max(R[i].ic[1], 0.0) for i in ids)
    pad = (hi - lo) * 0.06 or 1.0
    lo, hi = lo - pad, hi + pad
    pleines, nulles = [], []
    for i in ids:
        r, h, v = R[i], reg[i], synthese4.verdict(i)
        simple, enfant, exemple = clair4.CARTES[i]
        pcls, ptxt = PILULE[v]
        val, unite = _effet(r)
        u = (" " + unite) if unite else ""
        surv = '<span class="pill pill-ok">survit</span>' if synthese4.bilan(i)["survit"] else ""
        if v == "non établi":
            nulles.append(
                f'<details class="nul-card"><summary><span class="nul-ligne">'
                f'<span class="nul-id">{i}</span><span class="nul-nom">{_e(COURT[i])}</span>'
                f'<b>{val}{u}</b></span><span class="nul-5">{_e(enfant)}</span></summary>'
                f'<div class="nul-corps"><p class="res-clair">{_e(simple)}</p>'
                f'<div class="ex"><b>Exemple</b><p>{_e(exemple)}</p></div>'
                f'<p class="res-read">{_e(h.enonce)} — {_e(r.lecture)}</p>{_bat_ligne(i)}</div></details>')
            continue
        mcls = "ok" if v == "tient" else "ko"
        pleines.append(
            f'<article class="res res-{mcls}">'
            f'<div class="res-top"><span class="res-id">{i}</span>'
            f'<span class="res-court">{_e(COURT[i])}</span>'
            f'<span class="pill {pcls}">{ptxt}</span>{surv}</div>'
            f'<h3>{_e(h.enonce)}</h3>'
            f'<p class="res-num">{val}<small>{u}</small></p>'
            f'{_trois(simple, enfant, exemple)}'
            f'<details class="chiffres"><summary>Les chiffres et la batterie</summary>'
            f'<p class="res-read">{_e(r.lecture)}</p>{_mini(r, lo, hi, mcls)}{_bat_ligne(i)}</details></article>')
    out = '<div class="res-list">' + "".join(pleines) + "</div>"
    if nulles:
        out += (f'<p class="nuls-titre">Ce que les données ne montrent pas · {len(nulles)}</p>'
                f'<p class="nuls-aide">Touche une ligne pour l’explication et un exemple.</p>'
                f'<div class="nuls">' + "".join(nulles) + "</div>")
    return out


def etude(cle: str) -> str:
    quoi, enfant, exemple = clair4.ETUDES[cle]
    return ('<div class="comprendre">'
            f'<div class="cq"><p class="bloc-label">C’est quoi cette étude&nbsp;?</p><p>{_e(quoi)}</p></div>'
            f'<div class="kid5 grand"><b>Comme si tu avais 5 ans</b><p>{_e(enfant)}</p></div>'
            f'<div class="ex"><b>Exemple</b><p>{_e(exemple)}</p></div></div>')


def tests() -> str:
    out = []
    for k, (t, nom, regle) in enumerate(R4.TESTS, start=1):
        _, normal, enfant, exemple = clair4.TESTS_CLAIR[t]
        out.append(f'<article class="lit"><h3>{k}. {_e(nom)}</h3><p class="lit-0">{_e(normal)}</p>'
                   f'<p class="lit-1">Règle déclarée : {_e(regle)}.</p>'
                   f'<div class="kid5"><b>Comme si tu avais 5 ans</b><p>{_e(enfant)}</p></div>'
                   f'<div class="ex"><b>Exemple</b><p>{_e(exemple)}</p></div></article>')
    return '<div class="lits">' + "".join(out) + "</div>"


def batterie() -> str:
    out = []
    for i in synthese4.tous():
        b, v = synthese4.bilan(i), synthese4.verdict(i)
        pcls, ptxt = PILULE[v]
        etat = ('<span class="pill pill-ok">survit</span>' if b["survit"]
                else f'<span class="pill pill-nul">{b["passes"]}/{b["applicables"]}</span>')
        lignes = "".join(
            f'<dt>{k}. {_e(nom)}</dt><dd>{ {"passe": "passe", "echoue": "échoue", "sans objet": "sans objet"}[b["tests"][t]["etat"]] }'
            f'{(" — " + _e(b["tests"][t]["detail"])) if b["tests"][t]["detail"] else ""}</dd>'
            for k, (t, nom, _) in enumerate(R4.TESTS, start=1))
        out.append(f'<details class="reg"><summary><span class="res-id">{i}</span><span class="reg-nom">{_e(COURT[i])}</span>'
                   f'<span class="pill {pcls}">{ptxt}</span>{etat}</summary><div class="reg-corps"><dl>{lignes}</dl></div></details>')
    return '<p class="bloc-label">Les 25 idées, test par test</p><div class="regs">' + "".join(out) + "</div>"


def _lit(e: dict) -> str:
    ref = litterature4.REFS[e["ref"]] if e.get("ref") else None
    src = f'{_e(ref["court"])} ({ref["annee"]}) — ' if ref else ""
    enfant = f'<div class="kid5"><b>Comme si tu avais 5 ans</b><p>{_e(e["enfant"])}</p></div>' if e.get("enfant") else ""
    chiffre = f'<p class="res-num">{_e(e["chiffre"])}</p>' if e.get("chiffre") else ""
    return (f'<article class="lit"><h3>{_e(e["titre"])}</h3>{chiffre}<p class="lit-0">{_e(e["constat"])}</p>'
            f'<p class="lit-1">{src}{_e(e["preuve"])}</p>{enfant}</article>')


REGLES = ("nzfenix2024", "ue2024ai", "senat2026", "mastercard2021")
CONCURRENCE = ("camerer2004", "nagel1995", "mclean2016", "golder1993", "salganik2006")


def marche(regles: bool) -> str:
    items = [e for e in litterature4.MARCHE if (e["ref"] in REGLES) == regles]
    return '<div class="lits">' + "".join(_lit(e) for e in items) + "</div>"


def ailleurs(concurrence: bool) -> str:
    items = [e for e in litterature4.AILLEURS if (e["ref"] in CONCURRENCE) == concurrence]
    return '<div class="lits">' + "".join(_lit(e) for e in items) + "</div>"


def arene() -> str:
    C = calcul4.charger()["arene"]
    aff, sev = C["affirmations"], C["severe"]
    out = []
    for zid, enonce, seuil, mesure in R4.Z:
        a = aff[zid]
        question, enfant = clair4.Z_CLAIR[zid]
        pcls, ptxt = ("pill-ok", "tient") if a["tient"] else ("pill-nul", "ne tient pas")
        out.append(f'<article class="res res-{"ok" if a["tient"] else "nul"}"><div class="res-top"><span class="res-id">{zid}</span>'
                   f'<span class="res-court">seuil {_pc(seuil)}</span><span class="pill {pcls}">{ptxt}</span></div>'
                   f'<h3>{_e(enonce)}</h3><p class="res-num">{_pc(a["part"])}<small> des tirages</small></p>'
                   f'<p class="res-clair">{_e(question)}</p><div class="kid5"><b>Comme si tu avais 5 ans</b>'
                   f'<p>{_e(enfant)}</p></div><p class="res-read">Mesure déclarée : {_e(mesure)}. Variante sévère '
                   f'(le ciblage n’agit que sur la moitié du chat, non déclarée) : {_pc(sev[zid]["part"])}.</p></article>')
    cp = aff["copie"]["parts"]
    out.append('<article class="lit"><h3>Quand les autres copient</h3><p class="lit-0">Un coup d’avance reste devant la '
               f'mode dans {_pc(cp[0.1])} des tirages quand 10 % des concurrents jouent déjà le niveau 2, {_pc(cp[0.5])} '
               f'à 50 % et {_pc(cp[0.9])} à 90 % : l’avance ne s’use pas avec les imitateurs, mais elle reste sous le seuil '
               'de 90 %.</p></article>')
    t1, t10 = aff["top1"], aff["top10"]
    out.append('<article class="lit"><h3>Le premier centile</h3><p class="lit-0">Partie de la taille médiane, l’agence finit '
               'dans le premier centile dans ' + ", ".join(f"{_pc(t1[s])} ({R4.STRATEGIES[s].lower()})" for s in R4.STRATEGIES)
               + ' des tirages, et dans le premier décile dans ' + ", ".join(f"{_pc(t10[s], 1)}" for s in R4.STRATEGIES)
               + ' : la tactique fait monter le rang, la taille fait le premier centile.</p></article>')
    return '<div class="res-list">' + "".join(out) + "</div>"


def _phrase(t: str, vals: dict) -> str:
    t = _e(t)
    for k in sorted(vals, key=len, reverse=True):
        t = t.replace("{{" + k + "}}", vals[k])
    return t


def plan(vals: dict) -> str:
    out = []
    for k, p in enumerate(formation4.PLAN, start=1):
        preuves = "".join(
            f'<span class="pill {PILULE[synthese4.verdict(i)][0]}">{i} · {_e(COURT[i])}</span> ' for i in p["preuves"])
        refs = ", ".join(f'{_e(litterature4.REFS[r]["court"])} ({litterature4.REFS[r]["annee"]})' for r in p["refs"])
        etapes = "".join(f"<li>{_phrase(e, vals)}</li>" for e in p["etapes"])
        out.append(
            f'<article class="res res-ok" id="phase-{p["id"]}"><div class="res-top"><span class="res-id">Étape {k}</span>'
            f'<span class="res-court">{_e(p["titre"])}</span></div><h3>{_phrase(p["phrase"], vals)}</h3>'
            f'<div class="cq"><p class="bloc-label">Pourquoi</p><p>{_phrase(p["pourquoi"], vals)}</p>'
            f'{("<p>" + preuves + "</p>") if preuves else ""}{("<p class=\"lit-1\">" + refs + "</p>") if refs else ""}</div>'
            f'<div class="do"><b>Comment</b><ol class="etapes">{etapes}</ol></div>'
            f'<p class="res-read"><b>Ce que font les autres.</b> {_phrase(p["autres"], vals)}</p>'
            f'<p class="res-read"><b>Quand ils copient.</b> {_phrase(p["copie"], vals)}</p>'
            f'<div class="ex"><b>Le vérifier chez toi</b><p>{_phrase(p["verifier"], vals)}</p></div></article>')
    return '<div class="res-list">' + "".join(out) + "</div>"


def formation(vals: dict) -> str:
    out = []
    n = 0
    for m in formation4.MODULES:
        lecons = []
        for l in m["lecons"]:
            n += 1
            q, choix, bon, pourquoi = l["quiz"]
            faits = "".join(f"<li>{_phrase(f, vals)}</li>" for f in l["faits"])
            faire = "".join(f"<li>{_phrase(f, vals)}</li>" for f in l["faire"])
            eviter = "".join(f"<li>{_phrase(f, vals)}</li>" for f in l["eviter"])
            options = "".join(f"<li>{'✓ ' if j == bon else ''}{_phrase(c, vals)}</li>" for j, c in enumerate(choix))
            lecons.append(
                f'<details class="fold"><summary>Leçon {n} · {_e(l["titre"])}</summary>'
                f'<p class="lead">{_phrase(l["lead"], vals)}</p>'
                f'<div class="kid5"><b>Comme si tu avais 5 ans</b><p>{_phrase(l["kid"], vals)}</p></div>'
                f'<div class="cq"><p class="bloc-label">Ce qu’on sait</p><ul>{faits}</ul></div>'
                f'<div class="do"><b>À faire</b><ul>{faire}</ul></div>'
                f'<div class="warn"><b>À éviter</b><ul>{eviter}</ul></div>'
                f'<details class="chiffres"><summary>Question : {_phrase(q, vals)}</summary><ul>{options}</ul>'
                f'<p class="res-read">{_phrase(pourquoi, vals)}</p></details></details>')
        out.append(f'<div class="groupe"><h3 class="groupe-t">Module · {_e(m["titre"])}</h3>{"".join(lecons)}</div>')
    return "".join(out)


def faux() -> str:
    reg, R = R4.par_id(), synthese4.tous()
    out = []
    for i in R:
        v, b = synthese4.verdict(i), synthese4.bilan(i)
        if b["survit"]:
            continue
        simple, enfant, _ = clair4.CARTES[i]
        if v == "tient":
            tag = "tient, mais échoue : " + ", ".join(NOM_TEST[t].lower() for t in b["manque"])
        else:
            tag = v
        out.append(f'<article class="lit"><h3>{_e(reg[i].enonce)}</h3>'
                   f'<p class="lit-0">{i} · {_e(tag)} — {_e(R[i].lecture)}</p><p class="lit-1">{_e(simple)}</p>'
                   f'<div class="kid5"><b>Comme si tu avais 5 ans</b><p>{_e(enfant)}</p></div></article>')
    return '<div class="lits">' + "".join(out) + "</div>"


def registre_html() -> str:
    R, reg, q = synthese4.tous(), R4.par_id(), synthese4.q_valeurs()
    items = []
    for i, r in R.items():
        h, v = reg[i], synthese4.verdict(i)
        pcls, ptxt = PILULE[v]
        val, unite = _effet(r)
        p = "< 0,0001" if r.p < 1e-4 else _num(r.p, 4)
        qq = "< 0,0001" if q[i] < 1e-4 else _num(q[i], 4)
        sens = {1: "hausse attendue", -1: "baisse attendue", 0: "question ouverte"}[h.sens]
        items.append(
            f'<details class="reg" data-v="{ {"tient": "ok", "contraire": "ko", "non établi": "nul"}[v] }" '
            f'data-f="{i[0]}"><summary><span class="res-id">{i}</span>'
            f'<span class="reg-nom">{_e(COURT[i])}</span><span class="pill {pcls}">{ptxt}</span></summary>'
            f'<div class="reg-corps"><p class="reg-enonce">{_e(h.enonce)}</p>'
            f'<dl><dt>Mesure déclarée</dt><dd>{_e(h.mesure)}</dd>'
            f'<dt>Pari</dt><dd>{sens}</dd>'
            f'<dt>Ce que montrent les données</dt><dd>{_e(r.lecture)}</dd>'
            f'<dt>Effet [IC 95 %]</dt><dd>{val}{(" " + unite) if unite else ""} '
            f'[{_num(r.ic[0], 3)} ; {_num(r.ic[1], 3)}]</dd>'
            f'<dt>p · q · n</dt><dd>{p} · {qq} · {_num(r.n, 0)}</dd>'
            f'<dt>Méthode</dt><dd>{_e(r.methode)}</dd></dl></div></details>')
    return "".join(items)


def sources() -> str:
    items = sorted(litterature4.REFS.values(), key=lambda r: (r["auteurs"], r["annee"]))
    return '<ol class="refs">' + "".join(f"<li>{litterature4.html_ref(r)}</li>" for r in items) + "</ol>"


def provenance() -> str:
    out = []
    prov = {"cdnow": donnees.provenance()["cdnow"], **{k: donnees2.provenance()[k] for k in ("hillstrom", "lenta", "x5",
            "retail", "kickstarter")}, "x5_achats": donnees3.provenance()["x5_achats"], **donnees4.provenance()}
    for _, info in sorted(prov.items()):
        depot = info.get("depot", info.get("source", ""))
        version = info.get("commit", info.get("etag", ""))
        out.append(f'<li><b>{_e(info.get("titre", ""))}</b><span>{_e(str(depot).replace("https://", ""))}'
                   f' · {_e(str(version)[:28])}</span><code>{info["sha256_extrait"][:16]}</code></li>')
    return '<ul class="prov">' + "".join(out) + "</ul>"


def _figure(m: re.Match, figs: dict, vals: dict) -> str:
    cle, vue, legende = m.group(1), m.group(2), m.group(3).strip()
    if cle not in figs:
        raise KeyError(f"graphique inconnu : {cle}")
    voir, montre, agence = clair4.GRAPHIQUES[cle]
    for k in sorted(vals, key=len, reverse=True):
        legende = legende.replace("{{" + k + "}}", vals[k])
    return (f'<figure class="viz"><span class="viz-tag">vue {vue}</span>{figs[cle]}'
            f'<figcaption>{legende}</figcaption>'
            f'<div class="lire"><p class="bloc-label">Comment lire ce graphique</p>'
            f'<p><b>Ce que tu vois.</b> {_phrase(voir, vals)}</p>'
            f'<p><b>Ce que ça montre.</b> {_phrase(montre, vals)}</p>'
            f'<p class="lire-agence"><b>Pour ton agence.</b> {_phrase(agence, vals)}</p></div></figure>')


def espace(text: str, vals: dict) -> tuple[str, list[str], dict[str, str]]:
    corps = dict(re.findall(r'<section id="([a-z]+)">(.*?)</section>', text, flags=re.S))
    ordre = re.findall(r'<section id="([a-z]+)">', text)
    if [i for _, ids in GROUPES for i in ids] != ordre or set(SUJETS) != set(ordre):
        raise ValueError(f"les groupes de l'espace ne suivent pas les sections : {ordre}")
    titres, tuiles = {}, {}
    for i in ordre:
        nom, question, ico = SUJETS[i]
        nom = nom.replace("{n_hyp}", vals["n_hyp"]).replace("{n_lecons}", vals["n_lecons"])
        question = question.replace("{n_lecons}", vals["n_lecons"])
        c = corps[i]
        m = re.search(r'<p class="eyebrow">(\d+) ·', c)
        num = m.group(1) if m else ""
        titres[i] = f"{num} · {nom}" if num else nom
        minutes = max(1, round(_mots_lus(c) / MOTS_MINUTE))
        pied_t = lecteur = ""
        if i in FAMILLES_SECTION:
            ids = [h.id for h in R4.H if h.famille == FAMILLES_SECTION[i]]
            v = [synthese4.verdict(x) for x in ids]
            ok, ko = v.count("tient"), v.count("contraire")
            nul = len(v) - ok - ko
            segs = "".join(f'<i class="{k}" style="flex-grow:{x}"></i>'
                           for k, x in (("v-ok", ok), ("v-ko", ko), ("v-nul", nul)) if x)
            pied_t = (f'<span class="t-pied" aria-hidden="true"><span class="t-v" data-ok="{ok}" data-ko="{ko}" '
                      f'data-nul="{nul}">{segs}</span><span class="t-chiffre">{ok}/{len(v)}</span></span>')
            lecteur = f'<span class="sr-only">, {_phrase_verdicts(ok, ko, len(v))}</span>'
        tuiles[i] = (
            f'<a class="tuile" href="#{i}" data-id="{i}" data-nom="{_attr(nom)}" data-num="{num}" '
            f'data-min="{minutes}" data-q="{_attr(question)}"><span class="t-ico">{icone(ico)}</span>'
            f'<span class="t-nom">{_e(nom)}</span><span class="t-q">{_e(question)}</span>{lecteur}{pied_t}'
            f'<span class="t-coin"><span class="t-min">≈ {minutes} min</span>'
            f'<span class="t-lu">{icone("check")}Lu</span></span></a>')
    groupes = []
    for titre, ids in GROUPES:
        legende = ""
        if any('class="t-v"' in tuiles[i] for i in ids):
            legende = ('<p class="g-leg"><span><i class="v-ok"></i>tient</span>'
                       '<span><i class="v-ko"></i>contraire</span><span><i class="v-nul"></i>non établi</span></p>')
        groupes.append(f'<div class="groupe"><h2 class="groupe-t">{_e(titre)}</h2>{legende}'
                       f'<div class="tuiles">{"".join(tuiles[i] for i in ids)}</div></div>')
    return '<nav class="sujets" aria-label="Tous les sujets">' + "".join(groupes) + "</nav>", ordre, titres


def commun() -> tuple[str, str]:
    base = GABARIT_1.read_text(encoding="utf-8")
    tete = base[base.index('<meta name="claude:viewport-fit-sides"'):base.index("</style>") + len("</style>")]
    tete = tete.replace("  .m-line-gris { stroke: var(--muted); stroke-width: 1.8; }",
                        "  .m-line-gris { stroke: var(--muted); stroke-width: 1.8; }\n"
                        "  .m-line-r { fill: none; stroke: var(--red); stroke-width: 2.2; "
                        "stroke-linejoin: round; stroke-linecap: round; }\n"
                        "  ol.etapes { margin: .4em 0 0 1.1em; padding: 0; list-style: decimal; }\n"
                        "  ol.etapes li, .cq ul li, .do ul li, .warn ul li { margin: .25em 0; }")
    if ".m-line-r" not in tete:
        raise ValueError("la feuille du nº 1 a changé : la courbe rouge n'a pas trouvé sa place")
    pied_c = base[base.index('<nav class="dock"'):]
    for a, b in (("'ofm-cahier-lus'", "'ofm-cahier4-lus'"), ("'ofm-cahier-ou'", "'ofm-cahier4-ou'"),
                 ('placeholder="relance, prix, bonus…"', 'placeholder="témoin, arène, plan…"')):
        if a not in pied_c:
            raise ValueError(f"le pied du nº 1 a changé : {a}")
        pied_c = pied_c.replace(a, b)
    return tete, pied_c


def build() -> str:
    text = TEMPLATE.read_text(encoding="utf-8")
    tete, pied_c = commun()
    text = text.replace("{{TETE}}", tete).replace("{{COMMUN}}", pied_c)
    text = re.sub(r"\{\{ETUDE:([a-z0-9]+)\}\}", lambda m: etude(m.group(1)), text)
    vals = dict(valeurs())
    figs = rendre()
    vals["n_figs"] = str(len(figs))
    blocs = {"TESTS": tests(), "BATTERIE": batterie(), "MARCHE": marche(False), "MARCHE_REGLES": marche(True),
             "AILLEURS_CONCURRENCE": ailleurs(True), "AILLEURS": ailleurs(False), "ARENE": arene(),
             "PLAN": plan(vals), "FORMATION": formation(vals), "FAUX": faux(), "REGISTRE": registre_html(),
             "SOURCES": sources(), "PROVENANCE": provenance()}
    for k, b in blocs.items():
        text = text.replace("{{" + k + "}}", b)
    # Les valeurs d'abord : une légende de graphique peut en citer une, et sa fin « }} » couperait la balise.
    for key in sorted(vals, key=len, reverse=True):
        text = text.replace("{{" + key + "}}", vals[key])
    text = re.sub(r"\{\{FIG:([a-z0-9_]+)\|(2D|3D)\|(.+?)\}\}", lambda m: _figure(m, figs, vals), text, flags=re.S)
    text = re.sub(r"\{\{CARTES:([A-Z]\d\d)-([A-Z]\d\d)\}\}", lambda m: cartes(_ids(m.group(1), m.group(2))), text)
    hub, ordre, titres = espace(text, vals)
    text = text.replace("{{SUJETS}}", hub)
    text = re.sub(r'(<section id="([a-z]+)">.*?)(</section>)',
                  lambda m: m.group(1) + pied(m.group(2), ordre, titres) + m.group(3), text, flags=re.S)
    reste = re.findall(r"\{\{[^}]+\}\}", text)
    if reste:
        raise KeyError(f"balises non résolues : {sorted(set(reste))}")
    return _typo(text)


def sortie() -> dict:
    """Ce que Lueur pourra lire : valeurs, verdicts, survie, batterie, plan et formation, sans rien recopier."""
    reg, vals = R4.par_id(), valeurs()
    return {"cahier": "ofm4", "valeurs": vals,
            "verdicts": {i: synthese4.verdict(i) for i in synthese4.tous()},
            "survie": {i: synthese4.bilan(i)["survit"] for i in synthese4.tous()},
            "batterie": {i: {t: synthese4.bilan(i)["tests"][t]["etat"] for t, _, _ in R4.TESTS} for i in synthese4.tous()},
            "hypotheses": {i: {"enonce": reg[i].enonce, "court": COURT[i], "jeu": reg[i].jeu, "lecture": r.lecture}
                           for i, r in synthese4.tous().items()},
            "arene": {k: v["part"] for k, v in calcul4.charger()["arene"]["affirmations"].items() if k.startswith("Z")},
            "plan": [{"id": p["id"], "titre": p["titre"], "phrase": _phrase(p["phrase"], vals),
                      "preuves": list(p["preuves"]), "refs": list(p["refs"])} for p in formation4.PLAN],
            "formation": [{"module": m["titre"], "lecons": [l["titre"] for l in m["lecons"]]} for m in formation4.MODULES]}


def main() -> None:
    OUTPUT.write_text(build(), encoding="utf-8")
    VALEURS.write_text(json.dumps(sortie(), ensure_ascii=False, sort_keys=True, indent=0) + "\n", encoding="utf-8")
    print(f"écrit : {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size:,} octets) et {VALEURS.name}")


if __name__ == "__main__":
    main()
