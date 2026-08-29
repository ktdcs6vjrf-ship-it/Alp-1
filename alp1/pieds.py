"""Sortir la prose de pied hors du SVG, et la recomposer sous la figure.

Une phrase d'explication posée *dans* un graphique ne se recompose pas : elle
déborde du cadre sur les écrans étroits, chevauche les marques, et échappe à
la sélection comme à la recherche. Les lignes de pied sont donc extraites du
SVG et rendues sous la légende, où elles se comportent en texte.

Ce module existe parce que le traitement doit être le même pour les trois
documents. Il vivait dans `workingpaper`, et `discpaper` le lui empruntait ;
`paper` ne le faisait pas, faute de pouvoir importer `workingpaper` sans
cycle — `workingpaper` importe `paper`. Le résultat se voyait, et seulement
sur la page : six chevauchements dans le document court, dont trois sur des
phrases que les deux autres documents sortent de leur graphique.

La règle du dépôt reste celle-ci : **une figure se regarde.** C'est un
balayage au navigateur qui a trouvé la divergence, pas une relecture.
"""

from __future__ import annotations

import re

#: Le motif de texte SVG, avec ses classes, ses attributs et son corps.
TEXTE_SVG = re.compile(r'<text class="([^"]*)"([^>]*)>(.*?)</text>', re.S)

#: Au-delà de cette longueur, ce n'est plus une étiquette de marque.
LONGUEUR_PROSE = 55

#: Distance au bas du cadre qui définit la bande de pied.
MARGE_PIED = 90.0


def hauteur(svg: str) -> float:
    """Hauteur déclarée par le `viewBox`, en unités de la planche."""
    m = re.search(r'viewBox="0 0 [\d.]+ ([\d.]+)"', svg)
    return float(m.group(1)) if m else 0.0


def extraire(svg: str) -> tuple[str, list[str]]:
    """Sort la prose de pied de figure du SVG et la rend séparément.

    Ne touche ni aux étiquettes de panneau (`sub`), qui portent la structure
    de la figure, ni aux textes courts, qui sont des étiquettes de marque.
    """
    h, pieds = hauteur(svg), []

    def remplacer(m: re.Match) -> str:
        classes, attrs, corps = m.group(1).split(), m.group(2), m.group(3)
        texte = re.sub(r"<[^>]+>", "", corps).strip()
        if not ({"lg", "ax"} & set(classes)) or "sub" in classes:
            return m.group(0)
        # `keep` déclare une annotation : une phrase qui commente un élément
        # précis du tracé et qui n'a de sens qu'à sa place. Le secours de
        # longueur ci-dessous l'aurait sortie comme n'importe quelle prose.
        if "keep" in classes:
            return m.group(0)
        # `cap` déclare un pied de figure. La longueur ne sert plus que de
        # secours, pour les figures qui posent leur prose sans passer par
        # `Board.caption` : elle coupait en deux toute phrase dont la dernière
        # ligne tombait sous le seuil, laissant une moitié dans la note du
        # document et l'autre orpheline sous la figure.
        if "cap" not in classes and len(texte) <= LONGUEUR_PROSE:
            return m.group(0)
        y = re.search(r'y="(-?[\d.]+)"', attrs)
        if not y or float(y.group(1)) < h - MARGE_PIED:
            return m.group(0)
        pieds.append(texte)
        return ""

    return TEXTE_SVG.sub(remplacer, svg), pieds


#: Minuscules latines, à l'exclusion des lettres grecques et des symboles.
#: `µ` vaut U+00B5 et `σ` U+03C3 : aucune des deux n'est dans cet intervalle,
#: et c'est voulu — capitaliser `µ` donnerait `Μ`, qui n'est pas le même
#: caractère et ne veut plus rien dire.
_MINUSCULES = "abcdefghijklmnopqrstuvwxyzàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ"


def joindre(pieds: list[str]) -> str:
    """Recompose les lignes de pied en phrases.

    Chaque ligne reçoit son point final, sauf celle qui se termine par une
    virgule ou un point-virgule et qu'une autre suit : celle-là se poursuit,
    et la ponctuer la couperait en deux phrases dont la seconde commencerait
    en minuscule. Le cas s'est produit : « … au-delà du seuil. les signaux
    manqués sont ceux qui partaient. »

    **Et toute phrase qui commence prend sa majuscule.** Les lignes de pied
    sont écrites en fragments minuscules, ce qui est juste tant qu'elles se
    suivent dans une même phrase et faux dès qu'une phrase s'achève. Le
    défaut se lisait une quarantaine de fois dans les trois documents : « …
    aucune donnée de marché. la bande 3 σ est dépassée … ». La majuscule ne
    s'applique qu'aux minuscules latines : `µ` et `σ` ouvrent des pieds, et
    les capitaliser changerait le caractère.
    """
    sortie = []
    debut_de_phrase = True
    for i, ligne in enumerate(pieds):
        ligne = ligne.rstrip()
        if debut_de_phrase and ligne[:1] in _MINUSCULES:
            ligne = ligne[0].upper() + ligne[1:]
        continue_ = ligne.endswith((",", ";")) and i + 1 < len(pieds)
        if continue_ or ligne.endswith((".", "?", "!")):
            sortie.append(ligne)
        else:
            sortie.append(ligne.rstrip(" ,;") + ".")
        debut_de_phrase = not continue_
    return " ".join(sortie)


def figure_html(svg: str, numero: int, legende: str,
                classe: str = "plate") -> str:
    """Le bloc `<figure>` complet, prose de pied sortie et rendue dessous.

    Les trois documents composaient ce bloc chacun de leur côté, à quelques
    espaces près. Le rassembler ici est ce qui garantit qu'ils le composent
    pareil — c'est la divergence, et non le code, qui avait produit le défaut.
    """
    propre, pieds = extraire(svg)
    note = f'\n      <p class="note">{joindre(pieds)}</p>' if pieds else ""
    return (
        f'    <figure class="{classe}">\n'
        f'      <figcaption><span class="lab">Figure {numero}</span>'
        f' — {legende}</figcaption>\n'
        f'      <div class="scroll">{propre}</div>{note}\n'
        '    </figure>'
    )
