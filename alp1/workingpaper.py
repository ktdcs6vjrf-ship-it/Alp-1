"""Construction du document de travail : ALP-1 et ALP-2 réunis en un seul.

Le gabarit `docs/temps-de-marche-et-peremption.template.html` porte la prose des deux
documents, réordonnée en cinq parties et précédée d'un sommaire et d'une
partie de définitions. Ce module lui fournit ce qu'il réclame.

Trois clés existent des deux côtés avec des valeurs différentes. Elles sont
désambiguïsées plutôt que silencieusement écrasées :

    {{sigma1}}                volatilité posée par ALP-1 (1,25 pt)
    {{sigma1_a2}}             volatilité déduite par ALP-2 (3,04 pt)
    {{TABLE:assumptions}}     hypothèses d'ALP-1
    {{TABLE:a2_assumptions}}  hypothèses d'ALP-2
    {{TABLE:deflation}}       déflation du Sharpe, cadre ALP-1
    {{TABLE:a2_deflation}}    déflation du Sharpe, cadre ALP-2

La construction échoue si une balise reste non résolue, si une table citée
n'existe pas, ou si deux tables se disputent la même clé.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import lexicon, paper, paper2, quant, report, report2, report3
from .figalp2 import render_all as render_alp2_figures
from .figdecay import render_all as render_decay_figures
from .figcss import FIGURE_CSS, FIGURE_TOKENS_DARK, FIGURE_TOKENS_LIGHT
from .figquant import render_all as render_quant_figures
from .figterm import render_all as render_terminal_figures
from .figures import render_all as render_core_figures

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "docs" / "temps-de-marche-et-peremption.template.html"
OUTPUT = ROOT / "docs" / "temps-de-marche-et-peremption.html"

#: Clés produites par les deux documents avec des valeurs différentes. La
#: version ALP-2 est exposée sous un nom préfixé ; la version ALP-1 garde le
#: nom nu, puisque c'est elle que la prose des trois premières parties cite.
COLLISIONS_VALEURS = ("sigma1",)
COLLISIONS_TABLES = ("assumptions", "deflation")


def values() -> dict[str, str]:
    """Union des valeurs des deux documents, collisions préfixées."""
    v1, v2 = paper.values(), paper2.values()
    merged = dict(v1)
    for key, val in {**v2, **report3.values()}.items():
        if key in COLLISIONS_VALEURS:
            merged[f"{key}_a2"] = val
        elif key in merged and merged[key] != val:
            raise KeyError(
                f"collision de valeur non déclarée : {key!r} "
                f"vaut {merged[key]!r} pour ALP-1 et {val!r} pour ALP-2"
            )
        else:
            merged.setdefault(key, val)
    return merged


def tables() -> dict[str, report.Table]:
    """Union des tables des deux documents, collisions préfixées."""
    merged: dict[str, report.Table] = {
        **report.all_tables(),
        **lexicon.all_tables(),
        **quant.all_tables(),
        **report3.all_tables(),
    }
    for key, table in report2.all_tables().items():
        if key in COLLISIONS_TABLES:
            merged[f"a2_{key}"] = table
        elif key in merged:
            raise KeyError(f"collision de table non déclarée : {key!r}")
        else:
            merged[key] = table
    return merged


def figures() -> dict[str, str]:
    """Toutes les figures, tous modules confondus."""
    merged: dict[str, str] = {}
    for render in (render_core_figures, render_terminal_figures,
                   render_quant_figures, render_alp2_figures,
                   render_decay_figures):
        for key, svg in render().items():
            if key in merged:
                raise KeyError(f"collision de figure : {key!r}")
            merged[key] = svg
    return merged


#: Une phrase d'explication posée dans le SVG ne se recompose pas : elle
#: déborde du cadre sur les écrans étroits, chevauche les marques, et échappe
#: à la sélection comme à la recherche. Ces lignes sont donc extraites du
#: graphique et rendues sous la légende, où elles se comportent en texte.
_TEXTE_SVG = re.compile(r'<text class="([^"]*)"([^>]*)>(.*?)</text>', re.S)
_LONGUEUR_PROSE = 55      # au-delà, ce n'est plus une étiquette
_MARGE_PIED = 90.0        # distance au bas du cadre qui définit un pied


def _hauteur(svg: str) -> float:
    m = re.search(r'viewBox="0 0 [\d.]+ ([\d.]+)"', svg)
    return float(m.group(1)) if m else 0.0


def extraire_pieds(svg: str) -> tuple[str, list[str]]:
    """Sort la prose de pied de figure du SVG et la rend séparément.

    Ne touche ni aux étiquettes de panneau (`sub`), qui portent la structure
    de la figure, ni aux textes courts, qui sont des étiquettes de marque.
    """
    hauteur, pieds = _hauteur(svg), []

    def remplacer(m: re.Match) -> str:
        classes, attrs, corps = m.group(1).split(), m.group(2), m.group(3)
        texte = re.sub(r"<[^>]+>", "", corps).strip()
        if not ({"lg", "ax"} & set(classes)) or "sub" in classes:
            return m.group(0)
        if len(texte) <= _LONGUEUR_PROSE:
            return m.group(0)
        y = re.search(r'y="(-?[\d.]+)"', attrs)
        if not y or float(y.group(1)) < hauteur - _MARGE_PIED:
            return m.group(0)
        pieds.append(texte)
        return ""

    return _TEXTE_SVG.sub(remplacer, svg), pieds


def build() -> str:
    text = TEMPLATE.read_text(encoding="utf-8")

    text = text.replace("{{TOKENS_LIGHT}}", FIGURE_TOKENS_LIGHT.rstrip("\n") + "\n")
    text = text.replace("{{TOKENS_DARK}}", FIGURE_TOKENS_DARK.rstrip("\n") + "\n")
    text = text.replace("{{FIGURE_CSS}}", FIGURE_CSS.strip("\n"))

    # Les clés longues d'abord : sans cela `{{sigma1}}` mangerait le préfixe de
    # `{{sigma1_a2}}` et laisserait un `_a2` orphelin dans le texte.
    vals = values()
    for key in sorted(vals, key=len, reverse=True):
        text = text.replace("{{" + key + "}}", vals[key])

    tbl = tables()
    counter = {"n": 0}

    def sub_table(m: re.Match) -> str:
        counter["n"] += 1
        key = m.group(1)
        if key not in tbl:
            raise KeyError(f"table inconnue : {key}")
        return tbl[key].to_html(counter["n"])

    text = re.sub(r"\{\{TABLE:([a-z0-9_]+)\}\}", sub_table, text)

    figs = figures()
    fig_counter = {"n": 0}

    def sub_figure(m: re.Match) -> str:
        fig_counter["n"] += 1
        key, caption = m.group(1), m.group(2).strip()
        if key not in figs:
            raise KeyError(f"figure inconnue : {key}")
        svg, pieds = extraire_pieds(figs[key])
        note = ""
        if pieds:
            corps = " ".join(p.rstrip(" ,;") + "." if not p.rstrip().endswith((".", "?", "!"))
                             else p for p in pieds)
            note = f'\n      <p class="note">{corps}</p>'
        return (
            '    <figure class="plate">\n'
            f'      <figcaption><span class="lab">Figure {fig_counter["n"]}</span>'
            f' — {caption}</figcaption>\n'
            f'      <div class="scroll">{svg}</div>{note}\n'
            '    </figure>'
        )

    text = re.sub(r"\{\{FIGURE:([a-z0-9_]+)\|(.+?)\}\}", sub_figure, text, flags=re.S)

    leftovers = re.findall(r"\{\{[^}]+\}\}", text)
    if leftovers:
        raise KeyError(f"balises non résolues : {sorted(set(leftovers))}")
    return text


def main() -> None:
    OUTPUT.write_text(build(), encoding="utf-8")
    print(f"écrit : {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size:,} octets)")


if __name__ == "__main__":
    main()
