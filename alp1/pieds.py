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


def bandeau_html(cle: str) -> str:
    """La ligne de spéculation d'une figure, entièrement calculée.

    Une figure décrit ; elle ne dit pas ce qu'il en coûterait d'en tirer une
    position. Cette ligne le dit, et elle le dit dans les deux sens, sous
    chaque planche du document. Rien n'y est écrit : le module `speculation`
    la recalcule à chaque construction depuis la géométrie de la lecture, si
    bien qu'une correction de mesure s'y propage sans qu'on touche à une
    seule figure.

    Elle est délibérément muette de mise en forme. Deux cent quatorze
    exemplaires d'un bandeau voyant détruiraient la page ; ce qu'on veut est
    qu'on puisse le lire quand on le cherche et l'ignorer sinon.

    Renvoie la chaîne vide si la clé n'appartient à aucune famille déclarée,
    ce qui laisse les documents qui n'ont pas de feuille de spéculation
    exactement comme ils étaient.
    """
    from . import speculation as sp

    module = sp.module_d_une_figure(cle)
    if not module:
        return ""
    b = sp.bandeau(module)
    pc = sp._pc
    return (
        f'\n      <p class="spec"><span class="lab">Spéculation</span>'
        f' · {b.objet}'
        f' · à dérive nulle {pc(b.p_hausse[0], 1)} dans les deux sens'
        f' · à {sp.num(sp.DERIVES[-1], 1)} pt/h '
        f'{pc(b.p_hausse[-1], 1)} à la hausse contre '
        f'{pc(b.p_baisse[-1], 1)} à la baisse'
        f' · µ requis {sp.num(b.derive_requise, 2)} pt/h'
        f' · objectif à {sp.num(b.portee, 2)} σ de séance</p>'
    )


def figure_html(svg: str, numero: int, legende: str,
                classe: str = "plate", cle: str = "") -> str:
    """Le bloc `<figure>` complet, prose de pied sortie et rendue dessous.

    Les trois documents composaient ce bloc chacun de leur côté, à quelques
    espaces près. Le rassembler ici est ce qui garantit qu'ils le composent
    pareil — c'est la divergence, et non le code, qui avait produit le défaut.

    `cle` est la clé de la figure. Quand elle est donnée, le bloc porte en
    plus la ligne de spéculation : c'est ce qui fait qu'aucune planche du
    troisième document ne se regarde sans qu'on sache ce qu'une position y
    coûterait. Les deux autres documents ne la passent pas et sont donc
    rendus à l'octet près comme avant.
    """
    propre, pieds = extraire(svg)
    note = f'\n      <p class="note">{joindre(pieds)}</p>' if pieds else ""
    spec = bandeau_html(cle) if cle else ""
    return (
        f'    <figure class="{classe}">\n'
        f'      <figcaption><span class="lab">Figure {numero}</span>'
        f' — {legende}</figcaption>\n'
        f'      <div class="scroll">{propre}</div>{note}{spec}\n'
        '    </figure>'
    )
