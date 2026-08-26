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


#: Ponctuation double française : elle veut une espace insécable devant. Le
#: deux-points prend l'espace pleine, les trois autres l'espace fine, selon
#: l'usage de l'Imprimerie nationale.
_INSECABLE = {":": "\u00a0", ";": "\u202f", "!": "\u202f", "?": "\u202f"}


def typographie(html: str) -> str:
    """Passe typographique française sur le document rendu.

    Elle fait deux choses : l'apostrophe droite devient l'apostrophe courbe,
    et la ponctuation double reçoit son espace insécable.

    **Pourquoi à la construction et non dans les sources.** L'apostrophe
    droite est aussi le délimiteur de chaîne de Python ; une substitution dans
    les modules détruirait les f-chaînes qui bâtissent les figures. Faite ici,
    la passe couvre d'un coup le gabarit, les tables et les figures, et ne
    peut rien casser en amont.

    Elle ne touche qu'au **texte** : le contenu des balises `<style>` est mis
    de côté, et l'intérieur des balises — donc tout attribut — n'est jamais
    visité, ce qui protège les URL, les classes et les valeurs numériques.
    """
    # Le bloc de style est retiré puis remis : il contient des apostrophes de
    # nom de police qu'il ne faut surtout pas courber.
    avant, sep, reste = html.partition("<style>")
    style, sep2, apres = reste.partition("</style>")

    def texte_seul(fragment: str) -> str:
        out, i = [], 0
        while i < len(fragment):
            ouvre = fragment.find("<", i)
            if ouvre == -1:
                out.append(_corriger(fragment[i:]))
                break
            out.append(_corriger(fragment[i:ouvre]))
            ferme = fragment.find(">", ouvre)
            if ferme == -1:
                out.append(fragment[ouvre:])
                break
            out.append(fragment[ouvre:ferme + 1])
            i = ferme + 1
        return "".join(out)

    return texte_seul(avant) + sep + style + sep2 + texte_seul(apres)


def _corriger(txt: str) -> str:
    """Corrige un nœud de texte, jamais du balisage."""
    txt = txt.replace("'", "\u2019")
    out = []
    for i, ch in enumerate(txt):
        espace = _INSECABLE.get(ch)
        # On n'insère l'espace que derrière un mot déjà collé à la ponctuation :
        # une ponctuation déjà espacée, ou ouvrant un fragment, est laissée.
        if espace and i > 0 and (txt[i - 1].isalnum() or txt[i - 1] == "\u2019"):
            suivant = txt[i + 1] if i + 1 < len(txt) else " "
            if suivant in " \n\t<" or i + 1 == len(txt):
                out.append(espace)
        out.append(ch)
    return "".join(out)


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
    return typographie(text)


def main() -> None:
    OUTPUT.write_text(build(), encoding="utf-8")
    print(f"écrit : {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size:,} octets)")


if __name__ == "__main__":
    main()
