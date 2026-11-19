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

from . import donnees, papier, registre, synthese
from .figmobile import rendre
from .figures import COURT

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "docs" / "ofm" / "la-personne-mobile.template.html"
OUTPUT = ROOT / "docs" / "ofm" / "la-personne-mobile.html"

PILULE = {"tient": ("pill-ok", "tient"), "contraire": ("pill-ko", "contraire"),
          "non établi": ("pill-nul", "non établi")}


def _e(t: str) -> str:
    return H.escape(t, quote=True)


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


def cartes(lettre: str) -> str:
    """Cartes pleines pour ce qui tient ou contredit, lignes compactes pour le reste."""
    R, reg = synthese.tous(), registre.par_id()
    ids = [i for i in R if i.startswith(lettre)]
    lo = min(min(R[i].ic[0], 0.0) for i in ids)
    hi = max(max(R[i].ic[1], 0.0) for i in ids)
    pad = (hi - lo) * 0.06 or 1.0
    lo, hi = lo - pad, hi + pad
    pleines, nulles = [], []
    for i in ids:
        r, h, v = R[i], reg[i], synthese.verdict(i)
        pcls, ptxt = PILULE[v]
        val, unite = _effet(r)
        if v == "non établi":
            nulles.append(f'<li><span class="nul-id">{i}</span><span class="nul-nom">{_e(COURT[i])}</span>'
                          f'<b>{val}{(" " + unite) if unite else ""}</b></li>')
            continue
        mcls = "ok" if v == "tient" else "ko"
        pleines.append(
            f'<article class="res res-{mcls}">'
            f'<div class="res-top"><span class="res-id">{i}</span>'
            f'<span class="res-court">{_e(COURT[i])}</span>'
            f'<span class="pill {pcls}">{ptxt}</span></div>'
            f'<h3>{_e(h.enonce)}</h3>'
            f'<p class="res-num">{val}<small>{(" " + unite) if unite else ""}</small></p>'
            f'<p class="res-read">{_e(r.lecture)}</p>'
            f'{_mini(r, lo, hi, mcls)}'
            f'<p class="res-ofm">{_e(synthese.en_agence(i))}</p></article>')
    out = '<div class="res-list">' + "".join(pleines) + "</div>"
    if nulles:
        out += (f'<p class="nuls-titre">Non établi après correction · {len(nulles)}</p>'
                f'<ul class="nuls">' + "".join(nulles) + "</ul>")
    return out


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
        out.append(f'<article class="lit"><h3>{_e(titre)}</h3>{corps}</article>')
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
    vals = dict(papier.values())
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
