"""La version mobile du cahier nº 2, dans la direction artistique de Lueur.

Même page que le cahier nº 1 (`mobile.py`) : sa feuille de style, son dock,
sa recherche et son script sont **repris tels quels** du gabarit du nº 1 au
moment de la construction — un seul endroit à corriger pour les deux — à deux
clés près : la lecture et la reprise se rangent sous `ofm-cahier2-*`, pour que
les deux cahiers, servis par la même origine dans Lueur, ne se mélangent pas.

On modifie `docs/ofm/cahier-2-mobile.template.html`, puis
`python -m ofm.mobile2`. Balises :

- `{{clé}}` — une valeur de `valeurs()` ;
- `{{FIG:clé|vue|légende}}` — un graphique de `figmobile2` ;
- `{{CARTES:E01-E07}}` — les cartes des hypothèses de cet intervalle ;
- `{{ETUDE:clé}}`, `{{REGISTRE}}`, `{{AILLEURS}}`, `{{FAUX}}`, `{{SOURCES}}`,
  `{{PROVENANCE}}`, `{{SUJETS}}`, `{{TETE}}`, `{{COMMUN}}`.

La commande écrit aussi `docs/ofm/cahier-2-valeurs.json` : les valeurs et les
verdicts calculés, que l'app Lueur lit sans les recopier.
"""

from __future__ import annotations

import html as H
import json
import re
from pathlib import Path

from alp1.figterm import _num

from . import (cibler, clair2, donnees2, garder, litterature2, objectif, registre2, relancer,
               stats, synthese2)
from .figmobile2 import COURT, rendre
from .mobile import (MOTS_MINUTE, PILULE, TEMPLATE as GABARIT_1, _attr, _e, _effet, _mini,
                     _mots_lus, _phrase_verdicts, _trois, _typo, icone, pied)
from .resultat import entier
from .synthese import ENVOIS_SEMAINE, P_AGENCE

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "docs" / "ofm" / "cahier-2-mobile.template.html"
OUTPUT = ROOT / "docs" / "ofm" / "cahier-2-mobile.html"
VALEURS = ROOT / "docs" / "ofm" / "cahier-2-valeurs.json"

GROUPES = (
    ("Pour commencer", ("resume", "methode")),
    ("Les messages tirés au sort", ("courriel", "sms", "cibler")),
    ("Les marchés", ("garder", "objectif")),
    ("Passer à l'action", ("mesurer", "agir")),
    ("À savoir aussi", ("ailleurs", "faux")),
    ("Annexes", ("registre", "sources")),
)

SUJETS = {
    "resume": ("L'essentiel", "Ce qu'il faut retenir du cahier", "sparkles"),
    "methode": ("La méthode", "Pourquoi croire ces chiffres?", "pen-line"),
    "courriel": ("Le courriel", "Un message groupé fait-il acheter?", "messages-square"),
    "sms": ("Le SMS", "Sur qui le message agit-il?", "hand-coins"),
    "cibler": ("Cibler", "Qui relancer en premier?", "footprints"),
    "garder": ("Garder", "Le fidèle silencieux revient-il?", "rotate-ccw"),
    "objectif": ("L'objectif", "Une cagnotte affichée fait-elle payer?", "gift"),
    "mesurer": ("Mesurer chez soi", "Tester avec moins d'envois", "flask-conical"),
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


def valeurs() -> dict[str, str]:
    """Toutes les valeurs que la page et l'app citent, calculées."""
    R, c = synthese2.tous(), synthese2.comptes()
    q = synthese2.q_valeurs()
    passes = [r.p for i, r in R.items() if q[i] < synthese2.SEUIL_Q]
    v: dict[str, str] = {
        "n_hyp": str(c["total"]), "n_tient": str(c["tient"]), "n_contraire": str(c["contraire"]),
        "n_non": str(c["non"]), "n_nominal": str(c["nominal"]), "n_bruit": str(c["attendus_bruit"]),
        "n_survivent": str(c["tient"] + c["contraire"]),
        "z_bh": _num(abs(stats.Phi_inv(max(passes) / 2)), 2),
    }
    hs, le, x5 = donnees2.hillstrom(), donnees2.lenta(), donnees2.x5()
    ks, rt = objectif.campagnes(), garder.clients()
    v["n_obs"] = entier(len(hs) + len(le) + len(x5) + len(rt) + len(ks))
    v["n_marches"] = "5"
    # Le courriel.
    e1, e2, e3, e4 = R["E01"].extra, R["E02"].extra, R["E03"].extra, R["E04"].extra
    v.update({"hs_n": entier(len(hs)), "hs_vis_a": _p(e3["a"]), "hs_vis_b": _p(e3["b"]),
              "hs_ach_a": _p(e1["a"], 2), "hs_ach_b": _p(e1["b"], 2),
              "hs_ach_fois": _num(e1["a"] / e1["b"], 1),
              "hs_dep_a": _num(e2["a"], 2), "hs_dep_b": _num(e2["b"], 2),
              "e04_e": _s(R["E04"].effet, 1),
              "e04_h_bon": _p(e4["parts"]["hommes"][0]), "e04_h_autre": _p(e4["parts"]["hommes"][1]),
              "e04_f_bon": _p(e4["parts"]["femmes"][0]), "e04_f_autre": _p(e4["parts"]["femmes"][1])})
    # Le SMS.
    for k in ("E09", "E10", "E11", "E14", "E15", "E16"):
        v[f"{k.lower()}_oui"] = _s(R[k].extra["e1"] * 100)
        v[f"{k.lower()}_non"] = _s(R[k].extra["e0"] * 100)
    v.update({"le_n": entier(len(le)), "le_a": _p(R["E08"].extra["a"], 2), "le_b": _p(R["E08"].extra["b"], 2),
              "e08_e": _s(R["E08"].effet), "e12_e": _s(R["E12"].effet),
              "le_jamais": _p(R["E09"].extra["n0"] / (R["E09"].extra["n0"] + R["E09"].extra["n1"]), 0),
              "x5_n": entier(len(x5)), "x5_a": _p(R["E13"].extra["a"]), "x5_b": _p(R["E13"].extra["b"]),
              "e13_e": _s(R["E13"].effet, 1)})
    # Cibler.
    for jeu, k in (("hillstrom", "hs"), ("lenta", "le"), ("x5", "x5")):
        T = cibler.tiers(jeu)
        v[f"c_{k}_eff"] = _s(T["effet"][0] * 100)
        v[f"c_{k}_ris"] = _s(T["risque"][0] * 100)
        v[f"c_{k}_moy"] = _s(T["tous"][0] * 100)
        v[f"c_{k}_feff"] = _num(T["effet"][0] / T["tous"][0], 1)
        v[f"c_{k}_fris"] = _num(T["risque"][0] / T["tous"][0], 2)
        v[f"c_{k}_n"] = entier(T["n"])
    courbe = cibler.courbe("lenta", "effet", 10)
    part, gain = max(courbe, key=lambda t: t[1])
    v.update({"le_part_max": _num(part * 100, 0), "le_gain_max": _num(gain, 2),
              "le_gain_tous": _num(courbe[-1][1], 2)})
    # Garder.
    par = garder.par_frequence(4)
    g = R["G01"].extra
    v.update({"rt_n": entier(len(rt)), "rt_sil": entier(len(garder.silencieux())),
              "rt_x1_prev": _num(par[0][1], 2), "rt_x1_reel": _num(par[0][2], 2),
              "rt_x4_prev": _num(par[-1][1], 2), "rt_x4_reel": _num(par[-1][2], 2),
              "rt_mae_b": _num(g["mae_bgnbd"], 2), "rt_mae_n": _num(g["mae_naif"], 2),
              "g04_bg": _num(R["G04"].extra["bgnbd"] * 100, 1), "g04_dep": _num(R["G04"].extra["depense"] * 100, 1),
              "g05_med": _num(R["G05"].extra["mediane"], 0)})
    hauts = [c_["hold"] for c_ in rt if c_["dep_1"] > R["G05"].extra["mediane"]]
    bas = [c_["hold"] for c_ in rt if c_["dep_1"] <= R["G05"].extra["mediane"]]
    v.update({"g05_haut": _num(stats.moyenne(hauts), 1), "g05_bas": _num(stats.moyenne(bas), 1)})
    # L'objectif.
    e = objectif.entassement()
    pile, _ = objectif.pile()
    z, _, _ = objectif.reussite_duree_objectif()
    v.update({"ks_n": entier(len(ks)), "b01_haut": entier(e["ia"]), "b01_bas": entier(e["ib"]),
              "b01_attendu": _num((e["oa"] / e["ob"]) ** 0.25, 2), "ks_pile": entier(pile),
              "ks_base": _p(R["B02"].base), "b02_e": _s(R["B02"].effet, 1), "b03_e": _s(R["B03"].effet, 1),
              "b04_e": _s(R["B04"].effet, 1), "b05_e": _s(R["B05"].effet, 1),
              "ks_court_petit": _num(z[0][0], 0), "ks_long_petit": _num(z[-1][0], 0),
              "ks_30_grand": _num(z[2][3], 0)})
    # Mesurer.
    for k in ("M01", "M02", "M03"):
        v[f"{k.lower()}_r2"] = _num(R[k].extra["r2"] * 100, 1)
    n_achat, n_dep = relancer.budgets_hillstrom()
    v.update({"hs_n_achat": entier(n_achat), "hs_n_depense": entier(n_dep),
              "hs_fois_depense": _num(n_dep / n_achat, 1)})
    semaines = [synthese2.budget(i) / ENVOIS_SEMAINE for i in R
                if synthese2.budget(i) is not None and synthese2.verdict(i) == "tient"]
    v.update({"envois_semaine": entier(ENVOIS_SEMAINE), "p_agence": _num(P_AGENCE * 100, 0),
              "n_moins_mois": str(sum(1 for s in semaines if s < 52 / 12))})
    return v


def _ids(a: str, b: str) -> list[str]:
    ordre = [h.id for h in registre2.H]
    return ordre[ordre.index(a):ordre.index(b) + 1]


def cartes(ids: list[str]) -> str:
    R, reg = synthese2.tous(), registre2.par_id()
    lo = min(min(R[i].ic[0], 0.0) for i in ids)
    hi = max(max(R[i].ic[1], 0.0) for i in ids)
    pad = (hi - lo) * 0.06 or 1.0
    lo, hi = lo - pad, hi + pad
    pleines, nulles = [], []
    for i in ids:
        r, h, v = R[i], reg[i], synthese2.verdict(i)
        simple, enfant, exemple = clair2.CARTES[i]
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
            f'<p class="res-ofm">{_e(synthese2.en_agence(i))}</p></details></article>')
    out = '<div class="res-list">' + "".join(pleines) + "</div>"
    if nulles:
        out += (f'<p class="nuls-titre">Ce que les données ne montrent pas · {len(nulles)}</p>'
                f'<p class="nuls-aide">Touche une ligne pour l’explication et un exemple.</p>'
                f'<div class="nuls">' + "".join(nulles) + "</div>")
    return out


def etude(cle: str) -> str:
    quoi, enfant, exemple = clair2.ETUDES[cle]
    return ('<div class="comprendre">'
            f'<div class="cq"><p class="bloc-label">C’est quoi cette étude&nbsp;?</p><p>{quoi}</p></div>'
            f'<div class="kid5 grand"><b>Comme si tu avais 5 ans</b><p>{enfant}</p></div>'
            f'<div class="ex"><b>Exemple</b><p>{exemple}</p></div></div>')


def registre_html() -> str:
    R, reg, q = synthese2.tous(), registre2.par_id(), synthese2.q_valeurs()
    items = []
    for i, r in R.items():
        h, v = reg[i], synthese2.verdict(i)
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
    reg, R = registre2.par_id(), synthese2.tous()
    out = []
    for i in R:
        v = synthese2.verdict(i)
        if v == "tient":
            continue
        simple, enfant, _ = clair2.CARTES[i]
        tag = "contraire" if v == "contraire" else "non établi"
        out.append(f'<article class="lit"><h3>{_e(reg[i].enonce)}</h3>'
                   f'<p class="lit-0">{i} · {tag} — {_e(R[i].lecture)}</p><p class="lit-1">{_e(simple)}</p>'
                   f'<div class="kid5"><b>Comme si tu avais 5 ans</b><p>{_e(enfant)}</p></div></article>')
    return '<div class="lits">' + "".join(out) + "</div>"


def ailleurs() -> str:
    out = []
    for e in litterature2.AILLEURS:
        ref = litterature2.REFS[e["ref"]]
        out.append(f'<article class="lit"><h3>{_e(e["titre"])}</h3>'
                   f'<p class="lit-0">{_e(e["constat"])}</p>'
                   f'<p class="lit-1">{_e(ref["court"])} ({ref["annee"]}) — {_e(e["preuve"])}</p>'
                   f'<div class="kid5"><b>Comme si tu avais 5 ans</b><p>{_e(e["enfant"])}</p></div></article>')
    return '<div class="lits">' + "".join(out) + "</div>"


def sources() -> str:
    items = sorted(litterature2.REFS.values(), key=lambda r: (r["auteurs"], r["annee"]))
    return '<ol class="refs">' + "".join(f"<li>{litterature2.html_ref(r)}</li>" for r in items) + "</ol>"


def provenance() -> str:
    out = []
    for _, info in sorted(donnees2.provenance().items()):
        out.append(f'<li><b>{_e(info["titre"])}</b><span>{_e(info["depot"].replace("https://", ""))}'
                   f' · {_e(info["commit"][:28])}</span><code>{info["sha256_extrait"][:16]}</code></li>')
    return '<ul class="prov">' + "".join(out) + "</ul>"


def _figure(m: re.Match, figs: dict, vals: dict) -> str:
    cle, vue, legende = m.group(1), m.group(2), m.group(3).strip()
    if cle not in figs:
        raise KeyError(f"graphique inconnu : {cle}")
    voir, montre, agence = clair2.GRAPHIQUES[cle]

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
    v = [synthese2.verdict(i) for i in ids]
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
    for a, b in (("'ofm-cahier-lus'", "'ofm-cahier2-lus'"), ("'ofm-cahier-ou'", "'ofm-cahier2-ou'"),
                 ('placeholder="relance, prix, bonus…"', 'placeholder="relance, ciblage, objectif…"')):
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
    vals["n_refs"] = str(len(litterature2.REFS))
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
    reg = registre2.par_id()
    return {"cahier": "ofm2", "valeurs": valeurs(),
            "verdicts": {i: synthese2.verdict(i) for i in synthese2.tous()},
            "hypotheses": {i: {"enonce": reg[i].enonce, "court": COURT[i], "jeu": reg[i].jeu,
                               "lecture": r.lecture}
                           for i, r in synthese2.tous().items()}}


def main() -> None:
    OUTPUT.write_text(build(), encoding="utf-8")
    VALEURS.write_text(json.dumps(sortie(), ensure_ascii=False, sort_keys=True, indent=0) + "\n", encoding="utf-8")
    print(f"écrit : {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size:,} octets) et {VALEURS.name}")


if __name__ == "__main__":
    main()
