"""La version mobile du cahier nº 3, dans la direction artistique de Lueur.

Même page que les cahiers nº 1 et nº 2 (`mobile.py`, `mobile2.py`) : feuille de
style, dock, recherche et script **repris tels quels** du gabarit du nº 1 à la
construction, à trois clés près : la lecture et la reprise se rangent sous
`ofm-cahier3-*`, pour que les trois cahiers, servis par la même origine dans
Lueur, ne se mélangent pas ; la recherche propose ses propres mots.

On modifie `docs/ofm/cahier-3-mobile.template.html`, puis
`python -m ofm.mobile3`. Mêmes balises que le nº 2 (`{{clé}}`, `{{FIG:…}}`,
`{{CARTES:S01-S14}}`, `{{ETUDE:clé}}`, `{{REGISTRE}}`, `{{AILLEURS}}`,
`{{FAUX}}`, `{{SOURCES}}`, `{{PROVENANCE}}`, `{{SUJETS}}`, `{{TETE}}`,
`{{COMMUN}}`). La commande écrit aussi `docs/ofm/cahier-3-valeurs.json` : les
valeurs et les verdicts calculés, que l'app Lueur lit sans les recopier.
"""

from __future__ import annotations

import html as H
import json
import re
from functools import lru_cache
from pathlib import Path

from alp1.figterm import _num

from . import (clair3, donnees, donnees2, donnees3, leviers, litterature3, mobile, registre3,
               signaux, stats, synthese3)
from .figmobile3 import COURT, rendre
from .mobile import (MOTS_MINUTE, PILULE, TEMPLATE as GABARIT_1, _attr, _e, _effet, _mini,
                     _mots_lus, _phrase_verdicts, _trois, _typo, icone, pied)
from .resultat import entier
from .synthese import ENVOIS_SEMAINE, P_AGENCE

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "docs" / "ofm" / "cahier-3-mobile.template.html"
OUTPUT = ROOT / "docs" / "ofm" / "cahier-3-mobile.html"
VALEURS = ROOT / "docs" / "ofm" / "cahier-3-valeurs.json"

# Quatre pictogrammes de plus (dessins de Lucide, licence ISC), pour les sujets propres au nº 3.
mobile.ICONES.setdefault("activity", '<path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>')
mobile.ICONES.setdefault("trending-up", '<path d="M16 7h6v6"/><path d="m22 7-8.5 8.5-5-5L2 17"/>')
mobile.ICONES.setdefault("square-check", '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="m9 12 2 2 4-4"/>')
mobile.ICONES.setdefault("smile", '<circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" x2="9.01" y1="9" y2="9"/><line x1="15" x2="15.01" y1="9" y2="9"/>')

GROUPES = (
    ("Pour commencer", ("resume", "methode")),
    ("Les signaux", ("signaux", "backtest")),
    ("Les leviers tirés au sort", ("bonus", "preuve", "defaut", "sourire")),
    ("Passer à l'action", ("agir",)),
    ("À savoir aussi", ("ailleurs", "faux")),
    ("Annexes", ("registre", "sources")),
)

SUJETS = {
    "resume": ("L'essentiel", "Ce qu'il faut retenir du cahier", "sparkles"),
    "methode": ("La méthode", "Pourquoi croire ces chiffres?", "pen-line"),
    "signaux": ("Les signaux", "Que voit-on de plus que RFM?", "activity"),
    "backtest": ("Le backtest", "La liste des meilleurs fans, rejouée", "trending-up"),
    "bonus": ("Le petit cadeau", "Combien offrir pour faire agir?", "gift"),
    "preuve": ("Le premier don", "Dire que d'autres ont payé?", "handshake"),
    "defaut": ("La case cochée", "Ce qui est coché d'avance compte-t-il?", "square-check"),
    "sourire": ("Le sourire", "Une blague, et parler à hauteur des yeux", "smile"),
    "agir": ("Par où commencer", "Les gestes de la semaine", "check"),
    "ailleurs": ("Ailleurs", "Ce que d'autres études ont établi", "globe"),
    "faux": ("Ne tient pas", "Ce que les données ne montrent pas", "ban"),
    "registre": ("Les {n_hyp} idées", "Toutes, avec leur verdict", "list-checks"),
    "sources": ("Sources", "D'où viennent les chiffres", "book-marked"),
}


def _p(v: float, nd: int = 1) -> str:
    return _num(v * 100, nd)


def _s(v: float, nd: int = 2) -> str:
    """Un écart signé, à la française (+0,75 ; −0,12)."""
    return ("+" if v >= 0 else "−") + _num(abs(v), nd)


@lru_cache(maxsize=1)
def etalonnage() -> dict[str, int]:
    """Les essais de vérité connue que la méthode publie (déterministes)."""
    fp, n = signaux.etalonnage(100, 1500, 0.0)
    dur, nd = signaux.etalonnage(200, 2000, dur=True)
    p15, npw = signaux.etalonnage(40, 1500, 0.15)
    p30, _ = signaux.etalonnage(40, 1500, 0.3)
    return {"fp": fp, "n": n, "dur": dur, "nd": nd, "p15": p15, "p30": p30, "npw": npw}


def valeurs() -> dict[str, str]:
    """Toutes les valeurs que la page et l'app citent, calculées."""
    R, c = synthese3.tous(), synthese3.comptes()
    q = synthese3.q_valeurs()
    passes = [r.p for i, r in R.items() if q[i] < synthese3.SEUIL_Q]
    v: dict[str, str] = {
        "n_hyp": str(c["total"]), "n_tient": str(c["tient"]), "n_contraire": str(c["contraire"]),
        "n_non": str(c["non"]), "n_nominal": str(c["nominal"]), "n_bruit": str(c["attendus_bruit"]),
        "n_survivent": str(c["tient"] + c["contraire"]),
        "z_bh": _num(abs(stats.Phi_inv(max(passes) / 2)), 2),
    }
    clients = sum(len(signaux.table(j)) for j in signaux.JEUX)
    autres = len(donnees3.thornton()) + len(donnees3.rondeau()) + len(donnees3.cai()) + len(donnees3.gueguen()) \
        + len(donnees3.lynn())
    v["n_obs"] = entier(clients + autres)
    v["n_marches"] = str(len(signaux.JEUX) + len({h.jeu for h in registre3.H if h.famille == "L"}))
    # Les signaux.
    def ic(i: str) -> str:
        return _s(R[i].effet, 3)

    v.update({"acc_c": ic("S07"), "acc_r": ic("S08"), "acc_x": ic("S09"),
              "grp_c": ic("S01"), "grp_r": ic("S02"), "grp_x": ic("S03"),
              "elan_r": ic("S05"), "elan_x": ic("S06"), "pic_r": ic("S11"), "pic_x": ic("S12"),
              "var_x": ic("S14")})
    for k, i in (("acc_r2_c", "S07"), ("acc_r2_r", "S08"), ("acc_r2_x", "S09"), ("grp_r2_c", "S01"),
                 ("var_r2_x", "S14")):
        v[k] = _num(R[i].extra["r2"] * 100, 0)
    v["acc_r2_max"] = _num(max(R[i].extra["r2"] for i in ("S07", "S08", "S09")) * 100, 0)
    sig = [i for i in R if i in signaux.IDS.values()]
    v["n_sig"] = str(len(sig))
    v["n_sig_tient"] = str(sum(1 for i in sig if synthese3.verdict(i) == "tient"))
    za, _ = signaux.grille("acceleration", "x5")
    zg, _ = signaux.grille("groupement", "cdnow")
    v["acc_rap"] = _num(za[2][-1] / za[2][0], 2)
    v["grp_rap"] = _num(zg[2][-1] / zg[2][0], 2)
    for jeu, k in (("cdnow", "c"), ("retail", "r")):
        G = signaux.glissant(jeu)
        v[f"gl_acc_{k}"] = str(sum(1 for l in G if l["acceleration"][0] > l["acceleration"][2]))
        v[f"gl_grp_{k}"] = str(sum(1 for l in G if l["groupement"][0] < l["groupement"][1]))
    for jeu, k in (("cdnow", "c"), ("retail", "r"), ("x5", "x")):
        b = signaux.backtest(jeu)
        for cle in ("signaux", "rfm", "gros", "devin"):
            v[f"bt_{k}_{ {'signaux': 'sig'}.get(cle, cle) }"] = _num(b[cle] * 100, 1)
    e = etalonnage()
    v.update({"etal_fp": str(e["fp"]), "etal_essais": str(e["n"]), "etal_dur": str(e["dur"]),
              "etal_dur_essais": str(e["nd"]), "etal_p15": str(e["p15"]), "etal_p30": str(e["p30"]),
              "etal_pn": str(e["npw"])})
    # Les leviers.
    x1, x3 = R["L01"].extra, R["L03"].extra
    v.update({"th_n": entier(len(donnees3.thornton())), "th_avec": _p(x1["a"]), "th_sans": _p(x1["b"]),
              "th_dollar": _num(R["L02"].effet, 1), "th_p0": _p(x3["p0"]), "th_p1": _p(x3["p1"]),
              "th_p2": _p(x3["p2"]), "th_pas1": _num((x3["p1"] - x3["p0"]) * 100, 1),
              "th_reste": _num((x3["p2"] - x3["p1"]) * 100, 1), "th_km": _s(R["L04"].effet, 1)})
    T = donnees3.thornton()

    def part(bonus: int, a: float, b: float) -> str:
        rows = [r["retire"] for r in T if r["bonus"] == bonus and a <= r["distance"] < b]
        return _p(sum(rows) / len(rows))

    v.update({"th_d0_avec": part(1, 0, 1), "th_d3_avec": part(1, 3, 99), "th_d0_sans": part(0, 0, 1),
              "th_d3_sans": part(0, 3, 99)})
    rb = leviers.rondeau_bras()
    v.update({"ro_haut": _p(rb["temoin_haut"][0]), "ro_bas": _p(rb["temoin_bas"][0]),
              "ro_annonce": _p(rb["premier_don"][0]), "ro_double": _p(rb["doublement"][0]),
              "ro_lettres": entier(len(donnees3.rondeau())),
              "ro_min": _p(min(x[0] for x in rb.values())), "ro_max": _p(max(x[0] for x in rb.values())),
              "ro_budget": entier(synthese3.budget("L05"))})
    x10, x11 = R["L10"].extra, R["L11"].extra
    v.update({"cai_n": entier(len(donnees3.cai())), "cai_oui": _p(x10["a"]), "cai_non": _p(x10["b"]),
              "cai_det": _p(x11["a"]), "cai_simple": _p(x11["b"]),
              "cai_hameaux": str(len({r["hameau"] for r in donnees3.cai()}))})
    g = leviers.gueguen_bras()
    v.update({"gu_blague": _p(g["blague"][0]), "gu_pub": _p(g["publicite"][0]), "gu_aucune": _p(g["aucune"][0]),
              "gu_n": entier(len(donnees3.gueguen()))})
    x14 = R["L14"].extra
    v.update({"ly_acc": _num(x14["a"], 1), "ly_debout": _num(x14["b"], 1), "ly_n": entier(len(donnees3.lynn()))})
    for i in ("L01", "L10", "L13"):
        v[f"b_{i.lower()}"] = _num(synthese3.budget(i) / ENVOIS_SEMAINE, 1)
    semaines = [synthese3.budget(i) / ENVOIS_SEMAINE for i in R
                if synthese3.budget(i) is not None and synthese3.verdict(i) == "tient"]
    v.update({"envois_semaine": entier(ENVOIS_SEMAINE), "p_agence": _num(P_AGENCE * 100, 0),
              "n_moins_mois": str(sum(1 for s in semaines if s < 52 / 12))})
    return v


def _ids(a: str, b: str) -> list[str]:
    ordre = [h.id for h in registre3.H]
    return ordre[ordre.index(a):ordre.index(b) + 1]


def cartes(ids: list[str]) -> str:
    R, reg = synthese3.tous(), registre3.par_id()
    lo = min(min(R[i].ic[0], 0.0) for i in ids)
    hi = max(max(R[i].ic[1], 0.0) for i in ids)
    pad = (hi - lo) * 0.06 or 1.0
    lo, hi = lo - pad, hi + pad
    pleines, nulles = [], []
    for i in ids:
        r, h, v = R[i], reg[i], synthese3.verdict(i)
        simple, enfant, exemple = clair3.CARTES[i]
        pcls, ptxt = PILULE[v]
        val, unite = _effet(r)
        u = (" " + unite) if unite else ""
        if v == "non établi":
            nulles.append(
                f'<details class="nul-card"><summary><span class="nul-ligne">'
                f'<span class="nul-id">{i}</span><span class="nul-nom">{_e(COURT[i])}</span>'
                f'<b>{val}{u}</b></span><span class="nul-5">{_e(enfant)}</span></summary>'
                f'<div class="nul-corps"><p class="res-clair">{_e(simple)}</p>'
                f'<div class="ex"><b>Exemple</b><p>{_e(exemple)}</p></div>'
                f'<p class="res-read">{_e(h.enonce)} — {_e(r.lecture)}</p></div></details>')
            continue
        mcls = "ok" if v == "tient" else "ko"
        pleines.append(
            f'<article class="res res-{mcls}">'
            f'<div class="res-top"><span class="res-id">{i}</span>'
            f'<span class="res-court">{_e(COURT[i])}</span>'
            f'<span class="pill {pcls}">{ptxt}</span></div>'
            f'<h3>{_e(h.enonce)}</h3>'
            f'<p class="res-num">{val}<small>{u}</small></p>'
            f'{_trois(simple, enfant, exemple)}'
            f'<details class="chiffres"><summary>Les chiffres</summary>'
            f'<p class="res-read">{_e(r.lecture)}</p>{_mini(r, lo, hi, mcls)}'
            f'<p class="res-ofm">{_e(synthese3.en_agence(i))}</p></details></article>')
    out = '<div class="res-list">' + "".join(pleines) + "</div>"
    if nulles:
        out += (f'<p class="nuls-titre">Ce que les données ne montrent pas · {len(nulles)}</p>'
                f'<p class="nuls-aide">Touche une ligne pour l’explication et un exemple.</p>'
                f'<div class="nuls">' + "".join(nulles) + "</div>")
    return out


def etude(cle: str) -> str:
    quoi, enfant, exemple = clair3.ETUDES[cle]
    return ('<div class="comprendre">'
            f'<div class="cq"><p class="bloc-label">C’est quoi cette étude&nbsp;?</p><p>{quoi}</p></div>'
            f'<div class="kid5 grand"><b>Comme si tu avais 5 ans</b><p>{enfant}</p></div>'
            f'<div class="ex"><b>Exemple</b><p>{exemple}</p></div></div>')


def registre_html() -> str:
    R, reg, q = synthese3.tous(), registre3.par_id(), synthese3.q_valeurs()
    items = []
    for i, r in R.items():
        h, v = reg[i], synthese3.verdict(i)
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


def faux() -> str:
    """Les idées que les données ne soutiennent pas, et les deux contraires, calculées."""
    reg, R = registre3.par_id(), synthese3.tous()
    out = []
    for i in R:
        v = synthese3.verdict(i)
        if v == "tient":
            continue
        simple, enfant, _ = clair3.CARTES[i]
        tag = "contraire" if v == "contraire" else "non établi"
        out.append(f'<article class="lit"><h3>{_e(reg[i].enonce)}</h3>'
                   f'<p class="lit-0">{i} · {tag} — {_e(R[i].lecture)}</p><p class="lit-1">{_e(simple)}</p>'
                   f'<div class="kid5"><b>Comme si tu avais 5 ans</b><p>{_e(enfant)}</p></div></article>')
    return '<div class="lits">' + "".join(out) + "</div>"


def ailleurs() -> str:
    out = []
    for e in litterature3.AILLEURS:
        ref = litterature3.REFS[e["ref"]]
        out.append(f'<article class="lit"><h3>{_e(e["titre"])}</h3>'
                   f'<p class="lit-0">{_e(e["constat"])}</p>'
                   f'<p class="lit-1">{_e(ref["court"])} ({ref["annee"]}) — {_e(e["preuve"])}</p>'
                   f'<div class="kid5"><b>Comme si tu avais 5 ans</b><p>{_e(e["enfant"])}</p></div></article>')
    return '<div class="lits">' + "".join(out) + "</div>"


def sources() -> str:
    items = sorted(litterature3.REFS.values(), key=lambda r: (r["auteurs"], r["annee"]))
    return '<ol class="refs">' + "".join(f"<li>{litterature3.html_ref(r)}</li>" for r in items) + "</ol>"


def provenance() -> str:
    out = []
    prov = {"cdnow": donnees.provenance()["cdnow"], "retail": donnees2.provenance()["retail"],
            **donnees3.provenance()}
    for _, info in sorted(prov.items()):
        out.append(f'<li><b>{_e(info["titre"])}</b><span>{_e(info["depot"].replace("https://", ""))}'
                   f' · {_e(info["commit"][:28])}</span><code>{info["sha256_extrait"][:16]}</code></li>')
    return '<ul class="prov">' + "".join(out) + "</ul>"


def _figure(m: re.Match, figs: dict, vals: dict) -> str:
    cle, vue, legende = m.group(1), m.group(2), m.group(3).strip()
    if cle not in figs:
        raise KeyError(f"graphique inconnu : {cle}")
    voir, montre, agence = clair3.GRAPHIQUES[cle]

    def v(t: str) -> str:
        t = _e(t)
        for k in sorted(vals, key=len, reverse=True):
            t = t.replace("{{" + k + "}}", vals[k])
        return t

    return (f'<figure class="viz"><span class="viz-tag">vue {vue}</span>{figs[cle]}'
            f'<figcaption>{legende}</figcaption>'
            f'<div class="lire"><p class="bloc-label">Comment lire ce graphique</p>'
            f'<p><b>Ce que tu vois.</b> {v(voir)}</p>'
            f'<p><b>Ce que ça montre.</b> {v(montre)}</p>'
            f'<p class="lire-agence"><b>Pour ton agence.</b> {v(agence)}</p></div></figure>')


def _comptes(ids: list[str]) -> tuple[int, int, int]:
    v = [synthese3.verdict(i) for i in ids]
    ok, ko = v.count("tient"), v.count("contraire")
    return ok, ko, len(v) - ok - ko


def espace(text: str, gabarit: str, vals: dict) -> tuple[str, list[str], dict[str, str]]:
    corps = dict(re.findall(r'<section id="([a-z]+)">(.*?)</section>', text, flags=re.S))
    ordre = re.findall(r'<section id="([a-z]+)">', text)
    if [i for _, ids in GROUPES for i in ids] != ordre or set(SUJETS) != set(ordre):
        raise ValueError(f"les groupes de l'espace ne suivent pas les sections : {ordre}")
    familles: dict[str, list[str]] = {}
    for s, c in re.findall(r'<section id="([a-z]+)">(.*?)</section>', gabarit, flags=re.S):
        for a, b in re.findall(r"\{\{CARTES:([A-Z]\d\d)-([A-Z]\d\d)\}\}", c):
            familles.setdefault(s, []).extend(_ids(a, b))
    titres, tuiles = {}, {}
    for i in ordre:
        nom, question, ico = SUJETS[i]
        nom = nom.replace("{n_hyp}", vals["n_hyp"])
        c = corps[i]
        m = re.search(r'<p class="eyebrow">(\d+) ·', c)
        num = m.group(1) if m else ""
        titres[i] = f"{num} · {nom}" if num else nom
        minutes = max(1, round(_mots_lus(c) / MOTS_MINUTE))
        pied_t = lecteur = ""
        if i in familles:
            ok, ko, nul = _comptes(familles[i])
            n = ok + ko + nul
            segs = "".join(f'<i class="{k}" style="flex-grow:{x}"></i>'
                           for k, x in (("v-ok", ok), ("v-ko", ko), ("v-nul", nul)) if x)
            pied_t = (f'<span class="t-pied" aria-hidden="true"><span class="t-v" data-ok="{ok}" data-ko="{ko}" '
                      f'data-nul="{nul}">{segs}</span><span class="t-chiffre">{ok}/{n}</span></span>')
            lecteur = f'<span class="sr-only">, {_phrase_verdicts(ok, ko, n)}</span>'
        tuiles[i] = (
            f'<a class="tuile" href="#{i}" data-id="{i}" data-nom="{_attr(nom)}" data-num="{num}" '
            f'data-min="{minutes}" data-q="{_attr(question)}"><span class="t-ico">{icone(ico)}</span>'
            f'<span class="t-nom">{_e(nom)}</span><span class="t-q">{_e(question)}</span>{lecteur}{pied_t}'
            f'<span class="t-coin"><span class="t-min">≈ {minutes} min</span>'
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
    """La tête (polices, feuille) et le pied (dock, recherche, script) du gabarit nº 1."""
    base = GABARIT_1.read_text(encoding="utf-8")
    tete = base[base.index('<meta name="claude:viewport-fit-sides"'):base.index("</style>") + len("</style>")]
    tete = tete.replace("  .m-line-gris { stroke: var(--muted); stroke-width: 1.8; }",
                        "  .m-line-gris { stroke: var(--muted); stroke-width: 1.8; }\n"
                        "  .m-line-r { fill: none; stroke: var(--red); stroke-width: 2.2; "
                        "stroke-linejoin: round; stroke-linecap: round; }")
    if ".m-line-r" not in tete:
        raise ValueError("la feuille du nº 1 a changé : la courbe rouge n'a pas trouvé sa place")
    pied_c = base[base.index('<nav class="dock"'):]
    for a, b in (("'ofm-cahier-lus'", "'ofm-cahier3-lus'"), ("'ofm-cahier-ou'", "'ofm-cahier3-ou'"),
                 ('placeholder="relance, prix, bonus…"', 'placeholder="signal, bonus, case cochée…"')):
        if a not in pied_c:
            raise ValueError(f"le pied du nº 1 a changé : {a}")
        pied_c = pied_c.replace(a, b)
    return tete, pied_c


def build() -> str:
    text = gabarit = TEMPLATE.read_text(encoding="utf-8")
    tete, pied_c = commun()
    text = text.replace("{{TETE}}", tete).replace("{{COMMUN}}", pied_c)
    text = re.sub(r"\{\{ETUDE:([a-z]+)\}\}", lambda m: etude(m.group(1)), text)
    vals = valeurs()
    vals["n_refs"] = str(len(litterature3.REFS))
    figs = rendre()
    vals["n_figs"] = str(len(figs))
    for key in sorted(vals, key=len, reverse=True):
        text = text.replace("{{" + key + "}}", vals[key])
    text = re.sub(r"\{\{FIG:([a-z0-9_]+)\|(2D|3D)\|(.+?)\}\}", lambda m: _figure(m, figs, vals),
                  text, flags=re.S)
    text = re.sub(r"\{\{CARTES:([A-Z]\d\d)-([A-Z]\d\d)\}\}", lambda m: cartes(_ids(m.group(1), m.group(2))), text)
    text = text.replace("{{REGISTRE}}", registre_html()).replace("{{FAUX}}", faux())
    text = text.replace("{{AILLEURS}}", ailleurs()).replace("{{SOURCES}}", sources())
    text = text.replace("{{PROVENANCE}}", provenance())
    hub, ordre, titres = espace(text, gabarit, vals)
    text = text.replace("{{SUJETS}}", hub)
    text = re.sub(r'(<section id="([a-z]+)">.*?)(</section>)',
                  lambda m: m.group(1) + pied(m.group(2), ordre, titres) + m.group(3), text, flags=re.S)
    reste = re.findall(r"\{\{[^}]+\}\}", text)
    if reste:
        raise KeyError(f"balises non résolues : {sorted(set(reste))}")
    return _typo(text)


def sortie() -> dict:
    """Ce que Lueur lit : valeurs et verdicts calculés, avec le nom de chaque hypothèse."""
    reg = registre3.par_id()
    return {"cahier": "ofm3", "valeurs": valeurs(),
            "verdicts": {i: synthese3.verdict(i) for i in synthese3.tous()},
            "hypotheses": {i: {"enonce": reg[i].enonce, "court": COURT[i], "jeu": reg[i].jeu,
                               "lecture": r.lecture}
                           for i, r in synthese3.tous().items()}}


def main() -> None:
    OUTPUT.write_text(build(), encoding="utf-8")
    VALEURS.write_text(json.dumps(sortie(), ensure_ascii=False, sort_keys=True, indent=0) + "\n", encoding="utf-8")
    print(f"écrit : {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size:,} octets) et {VALEURS.name}")


if __name__ == "__main__":
    main()
