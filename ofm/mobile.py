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
- `{{REGISTRE}}`, `{{LISTE:clé}}`, `{{SOURCES}}`, `{{PROVENANCE}}` ;
- `{{SUJETS}}` — l'espace « Tous les sujets » : une tuile par section, rangées
  par `GROUPES`, chacune avec ses comptes **calculés** (verdicts de la famille,
  minutes de lecture). Chaque section reçoit aussi un pied
  « précédent / suivant / tous les sujets ».

Sur téléphone, la page s'ouvre sur cet espace et n'affiche qu'un sujet à la
fois (le script du gabarit) ; sans script, elle reste un long document précédé
de son sommaire.
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

# L'espace « Tous les sujets ». Les groupes suivent l'ordre des sections du
# gabarit (un test le vérifie) : la tuile suivante est toujours le sujet suivant.
GROUPES = (
    ("Pour commencer", ("resume", "methode")),
    ("Les marchés étudiés", ("demander", "offrir", "persuader", "negocier", "choisir", "revenir")),
    ("Passer à l'action", ("mesurer", "protocole")),
    ("À savoir aussi", ("ailleurs", "faux", "ecarte")),
    ("Annexes", ("registre", "sources")),
)

# Nom court, question à laquelle le sujet répond, icône. Aucun nombre ici :
# ceux des tuiles sont calculés à la construction (`{n_hyp}` compris).
SUJETS = {
    "resume": ("L'essentiel", "Ce qu'il faut retenir du cahier", "sparkles"),
    "methode": ("La méthode", "Pourquoi croire ces chiffres?", "pen-line"),
    "demander": ("Demander", "Qui obtient de l'argent d'un inconnu?", "hand-coins"),
    "offrir": ("Offrir", "Un bonus fait-il vraiment payer?", "gift"),
    "persuader": ("Persuader", "Une phrase peut-elle convaincre?", "messages-square"),
    "negocier": ("Négocier", "Que faire quand le fan marchande?", "handshake"),
    "choisir": ("Choisir", "Pourquoi dit-on oui?", "heart"),
    "revenir": ("Revenir", "Quels fans relancer en premier?", "rotate-ccw"),
    "mesurer": ("Mesurer chez soi", "Tester sans se tromper", "flask-conical"),
    "protocole": ("Par où commencer", "Les étapes d'un bon test", "footprints"),
    "ailleurs": ("Ailleurs", "Ce que d'autres études ont établi", "globe"),
    "faux": ("Ne tient pas", "Les astuces qui ne marchent pas", "ban"),
    "ecarte": ("Écarté", "Exclu, même quand ça marche", "shield-x"),
    "registre": ("Les {n_hyp} idées", "Toutes, avec leur verdict", "list-checks"),
    "sources": ("Sources", "D'où viennent les chiffres", "book-marked"),
}

# Le nom de chaque outil de la partie Mesurer, pour la recherche.
OUTILS_NOMS = {
    "paie": "Deviner le jour de paie d'un fan",
    "horloge": "Deviner l'heure d'un fan",
    "budget": "Combien d'envois pour prouver",
    "regarder": "Ne pas regarder son test tous les jours",
    "gagnant": "Le faux gagnant",
}

# Icônes : Lucide (licence ISC), la famille d'icônes de l'app Lueur.
ICONES = {
    "sparkles": '<path d="M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594z"/><path d="M20 2v4"/><path d="M22 4h-4"/><circle cx="4" cy="20" r="2"/>',
    "pen-line": '<path d="M13 21h8"/><path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/>',
    "hand-coins": '<path d="M11 15h2a2 2 0 1 0 0-4h-3c-.6 0-1.1.2-1.4.6L3 17"/><path d="m7 21 1.6-1.4c.3-.4.8-.6 1.4-.6h4c1.1 0 2.1-.4 2.8-1.2l4.6-4.4a2 2 0 0 0-2.75-2.91l-4.2 3.9"/><path d="m2 16 6 6"/><circle cx="16" cy="9" r="2.9"/><circle cx="6" cy="5" r="3"/>',
    "gift": '<path d="M12 7v14"/><path d="M20 11v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-8"/><path d="M7.5 7a1 1 0 0 1 0-5A4.8 8 0 0 1 12 7a4.8 8 0 0 1 4.5-5 1 1 0 0 1 0 5"/><rect x="3" y="7" width="18" height="4" rx="1"/>',
    "messages-square": '<path d="M16 10a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 2 14.286V4a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/><path d="M20 9a2 2 0 0 1 2 2v10.286a.71.71 0 0 1-1.212.502l-2.202-2.202A2 2 0 0 0 17.172 19H10a2 2 0 0 1-2-2v-1"/>',
    "handshake": '<path d="m11 17 2 2a1 1 0 1 0 3-3"/><path d="m14 14 2.5 2.5a1 1 0 1 0 3-3l-3.88-3.88a3 3 0 0 0-4.24 0l-.88.88a1 1 0 1 1-3-3l2.81-2.81a5.79 5.79 0 0 1 7.06-.87l.47.28a2 2 0 0 0 1.42.25L21 4"/><path d="m21 3 1 11h-2"/><path d="M3 3 2 14l6.5 6.5a1 1 0 1 0 3-3"/><path d="M3 4h8"/>',
    "heart": '<path d="M2 9.5a5.5 5.5 0 0 1 9.591-3.676.56.56 0 0 0 .818 0A5.49 5.49 0 0 1 22 9.5c0 2.29-1.5 4-3 5.5l-5.492 5.313a2 2 0 0 1-3 .019L5 15c-1.5-1.5-3-3.2-3-5.5"/>',
    "rotate-ccw": '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>',
    "flask-conical": '<path d="M14 2v6a2 2 0 0 0 .245.96l5.51 10.08A2 2 0 0 1 18 22H6a2 2 0 0 1-1.755-2.96l5.51-10.08A2 2 0 0 0 10 8V2"/><path d="M6.453 15h11.094"/><path d="M8.5 2h7"/>',
    "footprints": '<path d="M4 16v-2.38C4 11.5 2.97 10.5 3 8c.03-2.72 1.49-6 4.5-6C9.37 2 10 3.8 10 5.5c0 3.11-2 5.66-2 8.68V16a2 2 0 1 1-4 0Z"/><path d="M20 20v-2.38c0-2.12 1.03-3.12 1-5.62-.03-2.72-1.49-6-4.5-6C14.63 6 14 7.8 14 9.5c0 3.11 2 5.66 2 8.68V20a2 2 0 1 0 4 0Z"/><path d="M16 17h4"/><path d="M4 13h4"/>',
    "globe": '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>',
    "ban": '<circle cx="12" cy="12" r="10"/><path d="M4.929 4.929 19.07 19.071"/>',
    "shield-x": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m14.5 9.5-5 5"/><path d="m9.5 9.5 5 5"/>',
    "list-checks": '<path d="M13 5h8"/><path d="M13 12h8"/><path d="M13 19h8"/><path d="m3 17 2 2 4-4"/><path d="m3 7 2 2 4-4"/>',
    "book-marked": '<path d="M10 2v7.751a.25.25 0 00.407.195l2.28-1.834a.5.5 0 01.627 0l2.28 1.834A.25.25 0 0016 9.751V2"/><path d="M4 19.5v-15A2.5 2.5 0 016.5 2H19a1 1 0 011 1v18a1 1 0 01-1 1H6.5a1 1 0 010-5H20"/>',
    "layout-grid": '<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/>',
    "arrow-left": '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
    "arrow-right": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
}


def icone(nom: str, cls: str = "") -> str:
    c = f' class="{cls}"' if cls else ""
    return (f'<svg{c} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONES[nom]}</svg>')


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
    return (f'<div class="comprendre petit" data-nom="{_attr(OUTILS_NOMS[cle])}">'
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


def _figure(m: re.Match, figs: dict, vals: dict) -> str:
    """Un graphique, sa légende, et l'encadré « Comment lire ce graphique » :
    ce qu'on y voit, ce que ça montre, ce que l'agence en fait."""
    cle, vue, legende = m.group(1), m.group(2), m.group(3).strip()
    if cle not in figs:
        raise KeyError(f"graphique inconnu : {cle}")
    voir, montre, agence = clair.GRAPHIQUES[cle]

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


MOTS_MINUTE = 200  # vitesse de lecture déclarée, en mots par minute


def _attr(t: str) -> str:
    """Un texte d'attribut. La passe typographique ne visite jamais l'intérieur
    des balises : un attribut lu par le script (nom, question) se typographie
    ici, sinon il s'afficherait avec l'apostrophe droite."""
    return H.escape(typographie(t), quote=True)


def _mots_lus(fragment: str) -> int:
    """Les mots qu'on lit en ouvrant un sujet : ni le texte des graphiques, ni
    ce qui reste replié (« Les chiffres », « Pour les curieux »…)."""
    f = re.sub(r"<svg.*?</svg>", " ", fragment, flags=re.S)
    f = re.sub(r"<details[^>]*>\s*<summary>(.*?)</summary>.*?</details>", r" \1 ", f, flags=re.S)
    f = H.unescape(re.sub(r"<[^>]+>", " ", f))
    return sum(1 for m in f.split() if re.search(r"\w", m))


def _phrase_verdicts(ok: int, ko: int, n: int) -> str:
    if ok == 0:
        t = f"Aucune idée sur {n} ne tient"
    elif ok == 1:
        t = f"1 idée sur {n} tient"
    else:
        t = f"{ok} idées sur {n} tiennent"
    if ko:
        t += f", {ko} contraire{'s' if ko > 1 else ''}"
    return t


def _comptes(lettre: str) -> tuple[int, int, int]:
    """Tient, contraire, non établi : les verdicts calculés d'une famille."""
    v = [synthese.verdict(i) for i in synthese.tous() if i.startswith(lettre)]
    ok, ko = v.count("tient"), v.count("contraire")
    return ok, ko, len(v) - ok - ko


def espace(text: str, gabarit: str, vals: dict) -> tuple[str, list[str], dict[str, str]]:
    """L'espace « Tous les sujets » : une tuile par section, et l'ordre des sujets.

    Tout ce qu'une tuile compte est calculé : les verdicts viennent de
    `synthese`, les minutes des mots qu'on lit en ouvrant le sujet."""
    corps = dict(re.findall(r'<section id="([a-z]+)">(.*?)</section>', text, flags=re.S))
    ordre = re.findall(r'<section id="([a-z]+)">', text)
    if [i for _, ids in GROUPES for i in ids] != ordre or set(SUJETS) != set(ordre):
        raise ValueError(f"les groupes de l'espace ne suivent pas les sections : {ordre}")
    familles = {}
    for s, c in re.findall(r'<section id="([a-z]+)">(.*?)</section>', gabarit, flags=re.S):
        m = re.search(r"\{\{CARTES:([A-Z])\}\}", c)
        if m:
            familles[s] = m.group(1)

    titres, tuiles = {}, {}
    for i in ordre:
        nom, question, ico = SUJETS[i]
        nom = nom.replace("{n_hyp}", vals["n_hyp"])
        c = corps[i]
        m = re.search(r'<p class="eyebrow">(\d+) ·', c)
        num = m.group(1) if m else ""
        titres[i] = f"{num} · {nom}" if num else nom

        minutes = max(1, round(_mots_lus(c) / MOTS_MINUTE))
        pied = lecteur = ""
        if i in familles:
            ok, ko, nul = _comptes(familles[i])
            n = ok + ko + nul
            if n >= 2:
                segs = "".join(f'<i class="{k}" style="flex-grow:{v}"></i>'
                               for k, v in (("v-ok", ok), ("v-ko", ko), ("v-nul", nul)) if v)
                pied = (f'<span class="t-pied" aria-hidden="true"><span class="t-v" data-ok="{ok}" data-ko="{ko}" '
                        f'data-nul="{nul}">{segs}</span><span class="t-chiffre">{ok}/{n}</span></span>')
                lecteur = f'<span class="sr-only">, {_phrase_verdicts(ok, ko, n)}</span>'
        tuiles[i] = (
            f'<a class="tuile" href="#{i}" data-id="{i}" data-nom="{_attr(nom)}" data-num="{num}" '
            f'data-min="{minutes}" data-q="{_attr(question)}"><span class="t-ico">{icone(ico)}</span>'
            f'<span class="t-nom">{_e(nom)}</span><span class="t-q">{_e(question)}</span>{lecteur}{pied}'
            f'<span class="t-coin"><span class="t-min">≈\u00a0{minutes}\u00a0min</span>'
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


def pied(i: str, ordre: list[str], titres: dict[str, str]) -> str:
    """Le bas d'un sujet : le précédent, le suivant, et le retour à l'espace."""
    k = ordre.index(i)
    out = []
    if k > 0:
        p = ordre[k - 1]
        out.append(f'<a class="fin-prec" href="#{p}"><small>{icone("arrow-left")}Précédent</small>'
                   f'<b>{_e(titres[p])}</b></a>')
    if k + 1 < len(ordre):
        s = ordre[k + 1]
        out.append(f'<a class="fin-suiv" href="#{s}"><small>Suivant{icone("arrow-right")}</small>'
                   f'<b>{_e(titres[s])}</b></a>')
    out.append(f'<a class="fin-tous" href="#sujets">{icone("layout-grid")}Tous les sujets</a>')
    return '<nav class="fin" aria-label="Changer de sujet">' + "".join(out) + "</nav>"


def _typo(html: str) -> str:
    """La passe typographique du dépôt, scripts mis à l'abri.

    `typographie` épargne le bloc `<style>` et l'intérieur des balises, pas le
    contenu d'un `<script>` : elle courberait les apostrophes qui délimitent
    les chaînes JavaScript. On sort donc chaque script avant la passe.
    """
    morceaux = re.split(r"(<script>.*?</script>)", html, flags=re.S)
    return "".join(m if m.startswith("<script>") else typographie(m) for m in morceaux)


def build() -> str:
    text = gabarit = TEMPLATE.read_text(encoding="utf-8")
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
    text = re.sub(r"\{\{FIG:([a-z0-9_]+)\|(2D|3D)\|(.+?)\}\}", lambda m: _figure(m, figs, vals),
                  text, flags=re.S)
    text = re.sub(r"\{\{CARTES:([A-Z])\}\}", lambda m: cartes(m.group(1)), text)
    text = re.sub(r"\{\{LISTE:([a-z]+)\}\}", lambda m: liste(m.group(1)), text)
    text = text.replace("{{REGISTRE}}", registre_html())
    text = text.replace("{{SOURCES}}", refs)
    text = text.replace("{{PROVENANCE}}", provenance())
    hub, ordre, titres = espace(text, gabarit, vals)
    text = text.replace("{{SUJETS}}", hub)
    text = re.sub(r'(<section id="([a-z]+)">.*?)(</section>)',
                  lambda m: m.group(1) + pied(m.group(2), ordre, titres) + m.group(3), text, flags=re.S)
    reste = re.findall(r"\{\{[^}]+\}\}", text)
    if reste:
        raise KeyError(f"balises non résolues : {sorted(set(reste))}")
    return _typo(text)


def main() -> None:
    OUTPUT.write_text(build(), encoding="utf-8")
    print(f"écrit : {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size:,} octets)")


if __name__ == "__main__":
    main()
