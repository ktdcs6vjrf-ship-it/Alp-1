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

from . import (lexicon, paper, paper2, quant, report, report2, report3,
               report4, report5, report6, report7, report8, report9,
               report15)
from .figalp2 import render_all as render_alp2_figures
from .fighyp import render_all as render_hypothesis_figures
from .figdecay import render_all as render_decay_figures
from .figedge import render_all as render_edge_figures
from .figstrat import render_all as render_strat_figures
from .figpower import render_all as render_power_figures
from .figrisk import render_all as render_risk_figures
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
    for key, val in {**v2, **report3.values(), **report4.values(),
                     **report5.values(), **report6.values(),
                     **report7.values(),
                     **report8.values(), **report9.values(),
                     **report15.values()}.items():
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
        **report4.all_tables(),
        **report5.all_tables(),
        **report6.all_tables(),
        **report9.all_tables(),
        **report15.all_tables(),
        **report7.all_tables(),
        **report8.all_tables(),
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
                   render_decay_figures, render_power_figures,
                   render_edge_figures, render_risk_figures,
                   render_strat_figures, render_hypothesis_figures):
        for key, svg in render().items():
            if key in merged:
                raise KeyError(f"collision de figure : {key!r}")
            merged[key] = svg
    return merged


#: L'extraction de la prose de pied vit dans `alp1.pieds`, parce que les
#: trois documents doivent la faire pareil. Elle était définie ici, empruntée
#: par `discpaper`, et absente de `paper` — qui ne pouvait pas importer ce
#: module sans cycle. Le document court gardait donc sa prose dans ses SVG,
#: où elle chevauchait les marques. Les noms locaux sont conservés : ils sont
#: ce que les tests de ce document nomment.
from .pieds import extraire as extraire_pieds          # noqa: E402
from .pieds import figure_html, joindre as joindre_pieds   # noqa: E402
from .pieds import hauteur as _hauteur                 # noqa: E402
from .pieds import LONGUEUR_PROSE as _LONGUEUR_PROSE   # noqa: E402
from .pieds import MARGE_PIED as _MARGE_PIED           # noqa: E402


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
        return figure_html(figs[key], fig_counter["n"], caption)

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
