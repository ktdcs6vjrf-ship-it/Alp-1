"""Construction du document sur l'edge discrétionnaire.

Le document ne s'édite pas : on modifie `docs/edge-discretionnaire.template.html`
puis on relance `python main.py --discpaper`. Éditer le HTML produit le
mettrait en désaccord avec sa source au prochain build, et le désaccord ne se
verrait pas.

La chaîne est celle de `workingpaper.py`, réduite à un seul module de rapport
et un seul module de figures : jetons de style, valeurs scalaires, tables
numérotées, figures numérotées, puis un garde-fou qui refuse toute balise non
résolue. Ce dernier point importe plus qu'il n'y paraît — une clé mal
orthographiée produirait sinon un document où `{{d_mur_sr10}}` s'afficherait
tel quel au milieu d'une phrase.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import figdisc, report10
from .figcss import FIGURE_CSS, FIGURE_TOKENS_DARK, FIGURE_TOKENS_LIGHT
from .report import Table
from .workingpaper import extraire_pieds

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "docs" / "edge-discretionnaire.template.html"
OUTPUT = ROOT / "docs" / "edge-discretionnaire.html"


def values() -> dict[str, str]:
    """Les scalaires du document.

    Un seul module les fournit, donc aucune collision n'est possible ici —
    contrairement au document de travail, qui en fusionne neuf et doit
    déclarer ses collisions.
    """
    return report10.values()


def tables() -> dict[str, Table]:
    return report10.all_tables()


def figures() -> dict[str, str]:
    return figdisc.render_all()


def build() -> str:
    text = TEMPLATE.read_text(encoding="utf-8")

    text = text.replace("{{TOKENS_LIGHT}}", FIGURE_TOKENS_LIGHT.rstrip("\n") + "\n")
    text = text.replace("{{TOKENS_DARK}}", FIGURE_TOKENS_DARK.rstrip("\n") + "\n")
    text = text.replace("{{FIGURE_CSS}}", FIGURE_CSS.strip("\n"))

    # Les clés longues d'abord : sans cela une clé qui préfixe une autre
    # mangerait le début de sa voisine et laisserait un suffixe orphelin.
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
            corps = " ".join(
                p.rstrip(" ,;") + "." if not p.rstrip().endswith((".", "?", "!"))
                else p for p in pieds)
            note = f'\n      <p class="note">{corps}</p>'
        return (
            '    <figure class="plate">\n'
            f'      <figcaption><span class="lab">Figure {fig_counter["n"]}</span>'
            f' — {caption}</figcaption>\n'
            f'      <div class="scroll">{svg}</div>{note}\n'
            '    </figure>'
        )

    text = re.sub(r"\{\{FIGURE:([a-z0-9_]+)\|(.+?)\}\}", sub_figure, text,
                  flags=re.S)

    leftovers = re.findall(r"\{\{[^}]+\}\}", text)
    if leftovers:
        raise KeyError(f"balises non résolues : {sorted(set(leftovers))}")
    return text


def main() -> None:
    OUTPUT.write_text(build(), encoding="utf-8")
    print(f"écrit : {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size:,} octets)")


if __name__ == "__main__":
    main()
