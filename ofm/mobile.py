"""La version mobile du document nº 1, dans la direction artistique de Lueur.

Même source que le document de forme SSRN (`papier.py`) : les valeurs, les
verdicts, les tables et les références viennent des mêmes modules, si bien que
les deux versions ne peuvent pas diverger sur un chiffre. Seuls la mise en page
et les graphiques changent : une interface de téléphone (barre d'app, puces de
sections, cartes, dock du bas) et des graphiques en boîte de 340 unités avec
des blocs isométriques (`figmobile.py`).

On modifie `docs/ofm/la-personne-mobile.template.html`, puis
`python -m ofm.mobile`. Balises :

- `{{clé}}` — une valeur de `papier.values()` ;
- `{{FIG:clé|vue|légende}}` — un graphique de `figmobile`, vue « 2D » ou « 3D » ;
- `{{CARTES:X}}` — les cartes de résultats de la famille X du registre ;
- `{{REGISTRE}}`, `{{LISTE:clé}}`, `{{SOURCES}}`, `{{PROVENANCE}}`.
"""

from __future__ import annotations

import html as H
import re
from pathlib import Path

from alp1.discpaper import typographie
from alp1.figterm import _num

from . import clair, donnees, papier, registre, revenir, synthese
from .figmobile import rendre
from .figures import COURT

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "docs" / "ofm" / "la-personne-mobile.template.html"
OUTPUT = ROOT / "docs" / "ofm" / "la-personne-mobile.html"

PILULE = {"tient": ("pill-ok", "tient"), "contraire": ("pill-ko", "contraire"),
          "non établi": ("pill-nul", "non établi")}


def _e(t: str) -> str:
    """Échappe un **nœud de texte**. Les guillemets n'y ont rien à craindre ; les
    échapper changeait l'apostrophe en `&#x27;`, que la passe typographique ne
    reconnaît pas — et qui s'affichait droite dans toutes les cartes."""
    return H.escape(t, quote=False)


def _effet(r) -> str:
    nd = 2 if abs(r.effet) < 10 else 1
    if r.unite in ("pente", "r"):
        nd = 3
    signe = "+" if r.effet >= 0 else "−"
    unite = {"pt": "pt", "pt de prix": "pt de prix", "$": "$", "%": "%", "pente": "",
             "r": "", "achat": "achat", "achat par achat": "achat",
             "pt par point": "pt / point", "pt par 10 pt": "pt / 10 pt",
             "pt par point²": "pt / point²"}.get(r.unite, r.unite)
    return f"{signe}{_num(abs(r.effet), nd)}", unite


def _mini(r, lo: float, hi: float, cls: str) -> str:
    """Un intervalle à 95 % sur une règle commune à la famille, zéro marqué."""
    w, h, m = 300.0, 22.0, 6.0

    def x(v):
        return m + (min(max(v, lo), hi) - lo) / (hi - lo) * (w - 2 * m)

    z = x(0.0)
    return (f'<svg class="mini" viewBox="0 0 {w:g} {h:g}" aria-hidden="true">'
            f'<line class="mini-axe" x1="{m}" y1="11" x2="{w - m}" y2="11"/>'
            f'<line class="mini-zero" x1="{z:.1f}" y1="3" x2="{z:.1f}" y2="19"/>'
            f'<line class="mini-ic {cls}" x1="{x(r.ic[0]):.1f}" y1="11" x2="{x(r.ic[1]):.1f}" y2="11"/>'
            f'<circle class="mini-pt {cls}" cx="{x(r.effet):.1f}" cy="11" r="5"/></svg>')


def _trois(simple: str, enfant: str, exemple: str, titre_simple: str = "") -> str:
    """Les trois façons de dire la même chose : normalement, à un enfant, par un exemple."""
    tete = f'<p class="bloc-label">{titre_simple}</p>' if titre_simple else ""
    return (f'<p class="res-clair">{tete}{_e(simple)}</p>'
            f'<div class="kid5"><b>Comme si tu avais 5 ans</b><p>{_e(enfant)}</p></div>'
            f'<div class="ex"><b>Exemple</b><p>{_e(exemple)}</p></div>')


def cartes(lettre: str) -> str:
    """Ce qui tient : cartes ouvertes, l'explication d'abord, les chiffres repliés.
    Ce qui ne tient pas : une ligne par étude, sa phrase « 5 ans » visible, le
    reste au toucher. Chaque étude porte ses trois explications (`clair.CARTES`)."""
    R, reg = synthese.tous(), registre.par_id()
    ids = [i for i in R if i.startswith(lettre)]
    lo = min(min(R[i].ic[0], 0.0) for i in ids)
    hi = max(max(R[i].ic[1], 0.0) for i in ids)
    pad = (hi - lo) * 0.06 or 1.0
    lo, hi = lo - pad, hi + pad
    pleines, nulles = [], []
    for i in ids:
        r, h, v = R[i], reg[i], synthese.verdict(i)
        simple, enfant, exemple = clair.CARTES[i]
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
            f'<p class="res-ofm">{_e(synthese.en_agence(i))}</p></details></article>')
    out = '<div class="res-list">' + "".join(pleines) + "</div>"
    if nulles:
        out += (f'<p class="nuls-titre">Ce que les données ne montrent pas · {len(nulles)}</p>'
                f'<p class="nuls-aide">Touche une ligne pour l’explication et un exemple.</p>'
                f'<div class="nuls">' + "".join(nulles) + "</div>")
    return out


def etude(cle: str) -> str:
    quoi, enfant, exemple = clair.ETUDES[cle]
    return ('<div class="comprendre">'
            f'<div class="cq"><p class="bloc-label">C’est quoi cette étude&nbsp;?</p><p>{quoi}</p></div>'
            f'<div class="kid5 grand"><b>Comme si tu avais 5 ans</b><p>{enfant}</p></div>'
            f'<div class="ex"><b>Exemple</b><p>{exemple}</p></div></div>')


def outil(cle: str) -> str:
    simple, enfant, exemple = clair.OUTILS[cle]
    return ('<div class="comprendre petit">'
            f'<div class="cq"><p class="bloc-label">En clair</p><p>{_e(simple)}</p></div>'
            f'<div class="kid5"><b>Comme si tu avais 5 ans</b><p>{_e(enfant)}</p></div>'
            f'<div class="ex"><b>Exemple</b><p>{_e(exemple)}</p></div></div>')


def registre_html() -> str:
    R, reg, q = synthese.tous(), registre.par_id(), synthese.q_valeurs()
    items = []
    for i, r in R.items():
        h, v = reg[i], synthese.verdict(i)
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


def liste(cle: str) -> str:
    t = papier.tables()[cle]
    out = []
    for row in t.rows:
        titre, *reste = row
        # Les renvois « (section N) » visent la version longue : ils n'ont pas
        # de cible ici, où les sections ne sont pas numérotées pareil.
        reste = [re.sub(r"\s*\(section \d+\)", "", c) for c in reste]
        corps = "".join(f'<p class="lit-{k}">{_e(c)}</p>' for k, c in enumerate(reste))
        cinq = clair.LISTES[titre]
        out.append(f'<article class="lit"><h3>{_e(titre)}</h3>{corps}'
                   f'<div class="kid5"><b>Comme si tu avais 5 ans</b><p>{_e(cinq)}</p></div></article>')
    return '<div class="lits">' + "".join(out) + "</div>"


def sources() -> str:
    gab = papier.TEMPLATE.read_text(encoding="utf-8")
    bloc = gab[gab.index('<div class="refs">'):]
    bloc = bloc[:bloc.index("</div>")]
    return "<ol class=\"refs\">" + "".join(re.findall(r"<li>.*?</li>", bloc, flags=re.S)) + "</ol>"


def provenance() -> str:
    out = []
    for k, info in sorted(donnees.provenance().items()):
        sha = info["sha256_extrait"]
        sha = sha if isinstance(sha, str) else sha[0]
        out.append(f'<li><b>{_e(info["titre"])}</b><span>{_e(info["depot"].replace("https://", ""))}'
                   f' · {_e(info["commit"][:12])}</span><code>{sha[:16]}</code></li>')
    return '<ul class="prov">' + "".join(out) + "</ul>"


def _figure(m: re.Match, figs: dict) -> str:
    cle, vue, legende = m.group(1), m.group(2), m.group(3).strip()
    if cle not in figs:
        raise KeyError(f"graphique inconnu : {cle}")
    return (f'<figure class="viz"><span class="viz-tag">vue {vue}</span>{figs[cle]}'
            f'<figcaption>{legende}</figcaption></figure>')


def _typo(html: str) -> str:
    """La passe typographique du dépôt, scripts mis à l'abri.

    `typographie` épargne le bloc `<style>` et l'intérieur des balises, pas le
    contenu d'un `<script>` : elle courberait les apostrophes qui délimitent
    les chaînes JavaScript. On sort donc chaque script avant la passe.
    """
    morceaux = re.split(r"(<script>.*?</script>)", html, flags=re.S)
    return "".join(m if m.startswith("<script>") else typographie(m) for m in morceaux)


def build() -> str:
    text = TEMPLATE.read_text(encoding="utf-8")
    # Les explications d'étude portent elles-mêmes des balises de valeur :
    # elles se déplient avant la substitution des valeurs.
    text = re.sub(r"\{\{ETUDE:([a-z]+)\}\}", lambda m: etude(m.group(1)), text)
    text = re.sub(r"\{\{OUTIL:([a-z]+)\}\}", lambda m: outil(m.group(1)), text)
    vals = dict(papier.values())
    ex = revenir.exemple_silencieux()
    vals.update({"ex_cd_client": str(ex["client"]), "ex_cd_achats": str(ex["achats"]),
                 "ex_cd_mois1": ex["mois1"], "ex_cd_mois2": ex["mois2"],
                 "ex_cd_silence": _num(ex["silence"], 0), "ex_cd_pv": _num(ex["p_vivant"] * 100, 0),
                 "ex_cd_hold": str(ex["hold"]), "ex_cd_prevu": _num(ex["prevu"], 2)})
    refs = sources()
    vals["n_refs"] = str(refs.count("<li>"))
    vals["n_figs"] = str(len(rendre()))
    vals["n_marches"] = str(len(papier.tables()["jeux"].rows))
    for key in sorted(vals, key=len, reverse=True):
        text = text.replace("{{" + key + "}}", vals[key])
    figs = rendre()
    text = re.sub(r"\{\{FIG:([a-z0-9_]+)\|(2D|3D)\|(.+?)\}\}", lambda m: _figure(m, figs),
                  text, flags=re.S)
    text = re.sub(r"\{\{CARTES:([A-Z])\}\}", lambda m: cartes(m.group(1)), text)
    text = re.sub(r"\{\{LISTE:([a-z]+)\}\}", lambda m: liste(m.group(1)), text)
    text = text.replace("{{REGISTRE}}", registre_html())
    text = text.replace("{{SOURCES}}", refs)
    text = text.replace("{{PROVENANCE}}", provenance())
    reste = re.findall(r"\{\{[^}]+\}\}", text)
    if reste:
        raise KeyError(f"balises non résolues : {sorted(set(reste))}")
    return _typo(text)


def main() -> None:
    OUTPUT.write_text(build(), encoding="utf-8")
    print(f"écrit : {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size:,} octets)")


if __name__ == "__main__":
    main()
