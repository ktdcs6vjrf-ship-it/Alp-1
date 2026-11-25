"""Les graphiques de la version mobile du cahier nº 3.

Mêmes règles et même boîte que `figmobile.py` et `figmobile2.py` (340 unités,
aucune couleur écrite en dur, domaines déduits des données, libellés ARIA sans
apostrophe ni accent, une valeur au toucher sur chaque marque) ; les outils de
dessin en viennent. La couleur suit le verdict, jamais le rang : bleu pour ce
qui tient, rouge pour ce qui contredit le pari, gris pour ce qui reste dans le
bruit. Les courbes d'une même figure se distinguent aussi par leur trait.
"""

from __future__ import annotations

import math
from functools import lru_cache

from alp1.figterm import _num

from . import leviers, registre3, signaux, stats, synthese3
from .figmobile import W, Axes, Fig, Scene, _cls, _graduations, _grille_iso, _legende, _marque, _pct

#: Nom court de chaque hypothèse du registre nº 3 (bulles, cartes, registre).
COURT = {
    "S01": "Achats en grappes (CDNOW)", "S02": "Achats en grappes (Retail)", "S03": "Achats en grappes (X5)",
    "S04": "Élan (CDNOW)", "S05": "Élan (Retail)", "S06": "Élan (X5)",
    "S07": "Accélération (CDNOW)", "S08": "Accélération (Retail)", "S09": "Accélération (X5)",
    "S10": "Gros achat isolé (CDNOW)", "S11": "Gros achat isolé (Retail)", "S12": "Gros achat isolé (X5)",
    "S13": "Variété (Retail)", "S14": "Variété (X5)",
    "S15": "Dixième de tête (CDNOW)", "S16": "Dixième de tête (Retail)", "S17": "Dixième de tête (X5)",
    "L01": "Un bonus", "L02": "Un bonus plus gros", "L03": "Le premier pas", "L04": "La distance",
    "L05": "Premier don annoncé", "L06": "Annonce → argent", "L07": "Doublement promis",
    "L08": "Annonce contre doublement", "L09": "Objectif plus bas", "L10": "Case cochée d’avance",
    "L11": "Séance détaillée", "L12": "Blague contre rien", "L13": "Blague contre publicité",
    "L14": "À hauteur des yeux",
}

MARCHE_COURT = {"cdnow": "CDNOW", "retail": "Retail", "x5": "X5"}
NOM_SIGNAL = {"groupement": "Achats en grappes", "elan": "Élan", "acceleration": "Accélération",
              "pic": "Gros achat isolé", "variete": "Variété"}
FAMILLE_COURTE = {"S": "Signaux", "L": "Leviers"}

FIGURES: dict = {}


def _fig(cle: str):
    def deco(f):
        FIGURES[cle] = f
        return f
    return deco


def _pt(v: float, nd: int = 1) -> str:
    return ("+" if v >= 0 else "−") + _num(abs(v), nd) + " pt"


def _r(v: float) -> str:
    return ("+" if v >= 0 else "−") + _num(abs(v), 3)


# ---------------------------------------------------------------------------
# La chasse
# ---------------------------------------------------------------------------

@_fig("chasse3")
def m_chasse3() -> str:
    res, q = synthese3.tous(), synthese3.q_valeurs()
    passes = [r.p for i, r in res.items() if q[i] < synthese3.SEUIL_Q]
    zbh = abs(stats.Phi_inv(max(passes) / 2))
    fams = list(registre3.FAMILLES)
    rang = 56.0
    f = Fig(len(fams) * rang + 64, "Les trente et une hypotheses placees selon leur z oriente, "
                                   "famille par famille, avec le seuil corrige")
    ax = Axes(f, 70, 22, W - 88, len(fams) * rang, -5, 5, -0.5, len(fams) - 0.5)
    ax.band([(-1.96, -0.5), (1.96, -0.5)], [(-1.96, len(fams) - 0.5), (1.96, len(fams) - 0.5)])
    ax.vline(0.0, "m-axis")
    ax.vline(zbh, "m-seuil")
    ax.vline(-zbh, "m-seuil")
    for k, fa in enumerate(fams):
        yrow = len(fams) - 1 - k
        f.text(ax.x - 8, ax.sy(yrow) + 4, FAMILLE_COURTE[fa], "t-lab", "end")
        ids = [i for i in res if i.startswith(fa)]
        for j, i in enumerate(ids):
            z = synthese3.z_oriente(i)
            v = synthese3.verdict(i)
            ax.dot(min(max(z, -5), 5), yrow + ((j % 5) - 2) * 0.13, _cls(v),
                   tip=f"{i} {COURT[i]} — z {_num(z, 1)}, {v}", r=4.2)
    ax.ticks_x([-4, -2, 0, 2, 4], lambda v: _num(v, 0), "z orienté (dans le sens du pari)")
    return f.render()


@_fig("chasse3d")
def m_chasse3d() -> str:
    """Une colonne par famille, et pour les signaux une par marché : où l'avantage se trouve."""
    groupes = [("CDNOW", [i for i in synthese3.tous() if i.startswith("S") and registre3.par_id()[i].jeu == "cdnow"]),
               ("Retail", [i for i in synthese3.tous() if i.startswith("S") and registre3.par_id()[i].jeu == "retail"]),
               ("X5", [i for i in synthese3.tous() if i.startswith("S") and registre3.par_id()[i].jeu == "x5"]),
               ("Leviers", [i for i in synthese3.tous() if i.startswith("L")])]
    sc = Scene()
    pas, taille, unite = 32.0, 22.0, 9.0
    for k, (nom, ids) in enumerate(groupes):
        t = sum(1 for i in ids if synthese3.verdict(i) == "tient")
        c = sum(1 for i in ids if synthese3.verdict(i) == "contraire")
        n = len(ids) - t - c
        z0 = 0.0
        for nb, tone, ghost, quoi in ((t, "blue", False, "tiennent"), (c, "red", False, "contraires"),
                                      (n, "gray", True, "non établies")):
            if nb:
                sc.bloc(0, k * pas, taille, taille, nb * unite, tone, z=z0, ghost=ghost,
                        tip=f"{nom} : {nb} {quoi}")
                z0 += nb * unite
        sc.texte(taille, k * pas + taille / 2, 0, f"{nom}  {t + c}/{len(ids)}", "t-lab", "start", dx=10, dy=6)
    f = Fig(300, "Colonnes isometriques des hypotheses par marche des signaux et pour les leviers, "
                 "ce qui tient en bleu")
    bas = sc.rendre(f, 0, 0, W, 268)
    _legende(f, bas + 22, [("m-ok", "tient"), ("m-ko", "contraire"), ("m-nul", "non établi")])
    f.h = bas + 32
    return f.render()


# ---------------------------------------------------------------------------
# Les signaux
# ---------------------------------------------------------------------------

def _ids_signaux() -> list[str]:
    return [i for i in synthese3.tous() if i in signaux.IDS.values()]


@_fig("carte")
def m_carte() -> str:
    """La carte des signaux : à gauche ce que RFM ne contient pas, en haut ce qui prédit au-delà."""
    R = synthese3.tous()
    ids = _ids_signaux()
    f = Fig(286, "Chaque signal place selon la part que RFM en explique deja et selon ce quil predit "
                 "au dela de RFM, couleur du verdict")
    lo = min(min(R[i].ic[0] for i in ids), -0.02) * 1.15
    hi = max(max(R[i].ic[1] for i in ids), 0.02) * 1.15
    ax = Axes(f, 44, 26, W - 70, 196, 0, 1, lo, hi)
    ax.grid_y(_graduations(lo, hi, 4), lambda v: _r(v), "IC au-delà de RFM")
    ax.hline(0.0, "m-axis")
    ax.vline(0.5, "m-grid")
    for i in ids:
        r = R[i]
        x = min(max(r.extra["r2"], 0.0), 1.0)
        v = synthese3.verdict(i)
        ax.line([(x, r.ic[0]), (x, r.ic[1])], "m-ci-r" if v == "contraire" else "m-ci")
        ax.dot(x, r.effet, _cls(v), r=4.6,
               tip=f"{i} {COURT[i]} : IC {_r(r.effet)}, RFM en explique déjà {_num(x * 100, 0)} %, {v}")
    acc = [R[i] for i in ids if R[i].extra["signal"] == "acceleration"]
    xa = max(r.extra["r2"] for r in acc)
    ya = max(r.effet for r in acc)
    f.text(ax.sx(xa) + 12, ax.sy(ya) + 4, "accélération", "t-lab")
    ax.ticks_x([0, 0.25, 0.5, 0.75, 1], lambda v: _num(v * 100, 0) + " %", "part du signal déjà dans RFM")
    f.text(ax.x + 4, ax.y + 12, "pas encore dans le prix", "t-sub")
    f.text(ax.x + ax.w - 4, ax.y + 12, "déjà dans le prix", "t-sub", "end")
    _legende(f, 278, [("m-ok", "tient"), ("m-ko", "contraire"), ("m-nul", "non établi")])
    return f.render()


@_fig("ic_signaux")
def m_ic_signaux() -> str:
    """Un bloc par signal, une ligne par marché : l'IC au-delà de RFM, son intervalle, la bande du hasard."""
    R = synthese3.tous()
    ids = _ids_signaux()
    groupes: list[tuple[str, list[str]]] = []
    for i in ids:
        s = R[i].extra["signal"]
        if not groupes or groupes[-1][0] != s:
            groupes.append((s, []))
        groupes[-1][1].append(i)
    rang, tete = 19.0, 20.0
    hauteur = len(ids) * rang + len(groupes) * tete
    f = Fig(hauteur + 64, "IC au dela de RFM de chaque signal sur chaque marche, avec son "
                          "intervalle et la bande du hasard")
    lo = min(min(R[i].ic[0] for i in ids), min(R[i].extra["nul_bas"] for i in ids)) * 1.12
    hi = max(max(R[i].ic[1] for i in ids), max(R[i].extra["nul_haut"] for i in ids)) * 1.12
    ax = Axes(f, 62, 22, W - 72, hauteur, lo, hi, 0, hauteur)
    ax.vline(0.0, "m-axis")
    y = hauteur
    for s, liste in groupes:
        f.text(0, ax.sy(y - tete / 2) + 5, NOM_SIGNAL[s], "t-lab")
        y -= tete
        for i in liste:
            y -= rang
            yc = y + rang / 2
            r = R[i]
            v = synthese3.verdict(i)
            ax.hbar(yc, r.extra["nul_bas"], r.extra["nul_haut"], 11, "m-band",
                    tip=f"{COURT[i]} : 95 % du hasard entre {_r(r.extra['nul_bas'])} et {_r(r.extra['nul_haut'])}")
            ax.line([(r.ic[0], yc), (r.ic[1], yc)], "m-ci-r" if v == "contraire" else "m-ci")
            ax.dot(r.effet, yc, _cls(v), r=4.2, tip=f"{i} {COURT[i]} : IC {_r(r.effet)}, {v}")
            f.text(ax.x - 8, ax.sy(yc) + 4, MARCHE_COURT[r.extra["jeu"]], "t-ax", "end")
    ax.ticks_x(_graduations(lo, hi, 4), lambda v: _r(v), "IC au-delà de RFM")
    return f.render()


def par_niveau(z: list[list[float]]) -> list[list[float]]:
    """Chaque rangée (un niveau RFM) rapportée à sa moyenne : l'effet de RFM est retiré, celui du signal reste."""
    return [[v / (sum(l) / len(l)) for v in l] for l in z]


@_fig("relief_acc")
def m_relief_acc() -> str:
    z, n = signaux.grille("acceleration", "x5")
    rows = ["RFM bas", "", "RFM moyen", "", "RFM haut"]
    cols = ["ralentit", "", "", "", "accélère"]
    sc, _, _ = _grille_iso(par_niveau(z), rows, cols, lambda v: "×" + _num(v, 2),
                           "la dépense moyenne de son niveau RFM", taille=28, pas=36)
    f = Fig(300, "Blocs isometriques de la depense a venir selon le niveau RFM et la part de "
                 "lacceleration que RFM ne contient pas, chez X5")
    f.h = sc.rendre(f, 0, 0, W, 292) + 6
    return f.render()


@_fig("relief_grp")
def m_relief_grp() -> str:
    z, n = signaux.grille("groupement", "cdnow")
    rows = ["RFM bas", "", "RFM moyen", "", "RFM haut"]
    cols = ["réguliers", "", "", "", "en grappes"]
    sc, _, _ = _grille_iso(par_niveau(z), rows, cols, lambda v: "×" + _num(v, 2),
                           "la dépense moyenne de son niveau RFM", taille=28, pas=36)
    f = Fig(300, "Blocs isometriques de la depense a venir selon le niveau RFM et la part du "
                 "groupement que RFM ne contient pas, chez CDNOW")
    f.h = sc.rendre(f, 0, 0, W, 292) + 6
    return f.render()


@_fig("glissant")
def m_glissant() -> str:
    """À chaque coupe, l'IC de l'accélération (bleu) et du groupement (rouge), sur fond de hasard."""
    panneaux = [("cdnow", "CDNOW (validation de 26 semaines)"), ("retail", "Online Retail II (26 semaines)")]
    f = Fig(360, "IC au dela de RFM de lacceleration et du groupement a sept dates de coupe, "
                 "sur deux marches, avec la bande du hasard")
    hauteur = 112.0
    for p, (jeu, titre) in enumerate(panneaux):
        G = signaux.glissant(jeu)
        vals = [v for l in G for s in ("acceleration", "groupement") for v in l[s]]
        lo, hi = min(vals + [0.0]) * 1.2, max(vals + [0.0]) * 1.2
        y0 = 30 + p * (hauteur + 58)
        ax = Axes(f, 44, y0, W - 58, hauteur, -0.6, len(G) - 0.4, lo, hi)
        f.text(ax.x, y0 - 12, titre, "t-lab")
        ax.grid_y(_graduations(lo, hi, 3), lambda v: _r(v))
        bas = [(k, max(l["acceleration"][1], l["groupement"][1])) for k, l in enumerate(G)]
        haut = [(k, min(l["acceleration"][2], l["groupement"][2])) for k, l in enumerate(G)]
        ax.band(bas, haut)
        ax.hline(0.0, "m-axis")
        acc = [(k, l["acceleration"][0]) for k, l in enumerate(G)]
        grp = [(k, l["groupement"][0]) for k, l in enumerate(G)]
        ax.line(acc, "m-line-b")
        ax.line(grp, "m-line-r", "5 3")
        for k, l in enumerate(G):
            mois = l["coupe"][:7]
            ax.dot(k, l["acceleration"][0], "m-dot-b",
                   tip=f"{titre.split(' (')[0]}, coupe {mois} : accélération {_r(l['acceleration'][0])} ({l['n']} clients)")
            ax.dot(k, l["groupement"][0], "m-dot-r",
                   tip=f"{titre.split(' (')[0]}, coupe {mois} : groupement {_r(l['groupement'][0])}")
        etiq = {0: G[0]["coupe"][:7], len(G) - 1: G[-1]["coupe"][:7], len(G) // 2: G[len(G) // 2]["coupe"][:7]}
        ax.ticks_x(sorted(etiq), lambda v: etiq[int(v)].replace("-", "·"))
    _legende(f, 350, [("m-ok", "accélération"), ("m-ko", "achats en grappes (tirets)")])
    return f.render()


def _legende_traits(fig: Fig, y: float, items) -> None:
    """Légende en traits : (classe de trait, tirets, texte), deux par ligne."""
    for k, (cls, dash, texte) in enumerate(items):
        x, yy = (k % 2) * (W / 2), y + (k // 2) * 18
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        fig.add(f'<path class="{cls}" d="M{x:.1f},{yy - 4:.1f} L{x + 22:.1f},{yy - 4:.1f}"{extra}/>')
        fig.text(x + 28, yy, texte, "t-ax")


@_fig("capture")
def m_capture() -> str:
    b = signaux.backtest("cdnow")
    c = b["courbes"]
    f = Fig(286, "Part de la depense a venir tenue par les fans du haut de chaque classement, "
                 "selon la part contactee, chez CDNOW")
    ax = Axes(f, 44, 24, W - 64, 176, 0, 0.5, 0, 1)
    ax.grid_y([0, 0.25, 0.5, 0.75, 1], lambda v: _pct(v, 0), "part de la dépense à venir")
    series = (("devin", "m-line-gris", "1.5 3", "un devin"), ("gros", "m-line-gris", "6 4", "gros dépensiers"),
              ("rfm", "m-line-gris", "", "RFM seul"), ("signaux", "m-line-b", "", "RFM + signaux"))
    for cle, cls, dash, nom in series:
        ax.line([(0.0, 0.0)] + list(zip(c["parts"], c[cle])), cls, dash)
    ax.vline(registre3.PART_CONTACTEE, "m-seuil")
    k = int(round(registre3.PART_CONTACTEE * 100)) - 1
    for cle, nom in (("signaux", "RFM + signaux"), ("rfm", "RFM seul"), ("gros", "gros dépensiers"), ("devin", "un devin")):
        ax.dot(c["parts"][k], c[cle][k], "m-dot-b" if cle == "signaux" else "m-dot-g",
               tip=f"10 % contactés, {nom} : {_pct(c[cle][k])} de la dépense à venir")
    ax.ticks_x([0.1, 0.2, 0.3, 0.4, 0.5], lambda v: _num(v * 100, 0) + " %", "part des fans contactés")
    _legende_traits(f, 254, [(cls, dash, nom) for _, cls, dash, nom in reversed(series)])
    return f.render()


@_fig("capture_iso")
def m_capture_iso() -> str:
    z, rows = [], []
    for jeu in signaux.JEUX:
        b = signaux.backtest(jeu)
        z.append([b["gros"] * 100, b["rfm"] * 100, b["signaux"] * 100, b["devin"] * 100])
        rows.append(MARCHE_COURT[jeu])
    sc, _, _ = _grille_iso(z, rows, ["gros", "RFM", "+ signaux", "devin"],
                           lambda v: _num(v, 1) + " %", "de la dépense à venir dans le dixième de tête",
                           taille=26, pas=34)
    f = Fig(300, "Blocs isometriques de la part de la depense a venir tenue par le dixieme de tete "
                 "de quatre classements, sur trois marches")
    f.h = sc.rendre(f, 0, 0, W - 18, 292) + 6
    return f.render()


# ---------------------------------------------------------------------------
# Les leviers
# ---------------------------------------------------------------------------

#: Les tranches de `leviers.dose_reponse`, par leur borne haute.
ETIQUETTE_BONUS = ("rien", "0,25", "0,50", "1", "1,50", "2", "2 +")


@_fig("bonus_dose")
def m_bonus_dose() -> str:
    d = leviers.dose_reponse()
    f = Fig(236, "Part qui va chercher son resultat selon le bonus tire au sort, avec la marge du hasard")
    ax = Axes(f, 44, 24, W - 54, 150, -0.6, len(d) - 0.4, 0, 1)
    ax.grid_y([0, 0.25, 0.5, 0.75, 1], lambda v: _pct(v, 0), "vont chercher leur résultat")
    for k, (nom, p, n) in enumerate(d):
        h = 1.96 * math.sqrt(p * (1 - p) / n)
        ax.bar(k, 0, p, 26, "m-bar2" if k == 0 else "m-bar", tip=f"bonus {nom} : {_pct(p)} ({n} personnes)")
        ax.line([(k, max(p - h, 0)), (k, min(p + h, 1))], "m-ci")
        f.text(ax.sx(k), ax.y + ax.h + 14, ETIQUETTE_BONUS[k], "t-ax", "middle")
    f.text(ax.x + ax.w, ax.y + ax.h + 29, "bonus en dollars, jusqu’à ce montant", "t-sub", "end")
    return f.render()


@_fig("bonus_iso")
def m_bonus_iso() -> str:
    z, rows, cols, nb = leviers.grille_bonus_distance()
    sc = Scene()
    plat = [v for l in z for v in l]
    hi = max(plat)
    pas, taille = 38.0, 28.0
    for i in range(len(z)):
        for j in range(len(z[0])):
            v = z[i][j]
            sc.bloc(j * pas, i * pas, taille, taille, max(3.0, v / hi * 96.0), "blue" if i else "gray",
                    tip=f"bonus {rows[i]} · {cols[j]} : {_pct(v)} vont chercher leur résultat ({nb[i][j]} personnes)")
    X, Y = (len(z[0]) - 1) * pas + taille, (len(z) - 1) * pas + taille
    for i, lab in enumerate(rows):
        sc.texte(X, i * pas + taille / 2, 0, f"bonus {lab}", "t-lab", "start", dx=8, dy=8, groupe="lignes")
    for j, lab in enumerate(cols):
        sc.texte(j * pas + taille / 2, Y, 0, lab, "t-lab", "end", dx=-8, dy=12, groupe="colonnes")
    f = Fig(300, "Blocs isometriques de la part qui va chercher son resultat selon le bonus et la "
                 "distance au centre")
    f.h = sc.rendre(f, 0, 0, W, 292) + 6
    return f.render()


@_fig("distance")
def m_distance() -> str:
    T = leviers.donnees3.thornton()
    tranches = ((0.0, 1.0, "< 1"), (1.0, 2.0, "1–2"), (2.0, 3.0, "2–3"), (3.0, 99.0, "≥ 3"))
    avec, sans = [], []
    for k, (a, b, nom) in enumerate(tranches):
        for liste, test in ((avec, 1), (sans, 0)):
            rows = [r["retire"] for r in T if r["bonus"] == test and a <= r["distance"] < b]
            liste.append((k, sum(rows) / len(rows), len(rows), nom))
    f = Fig(240, "Part qui va chercher son resultat selon la distance au centre, avec et sans bonus")
    ax = Axes(f, 44, 24, W - 58, 150, -0.3, len(tranches) - 0.7, 0, 1)
    ax.grid_y([0, 0.25, 0.5, 0.75, 1], lambda v: _pct(v, 0), "vont chercher leur résultat")
    ax.line([(k, p) for k, p, _, _ in avec], "m-line-b")
    ax.line([(k, p) for k, p, _, _ in sans], "m-line-gris", "5 3")
    for k, p, n, nom in avec:
        ax.dot(k, p, "m-dot-b", tip=f"avec bonus, {nom} km : {_pct(p)} ({n} personnes)")
    for k, p, n, nom in sans:
        ax.dot(k, p, "m-dot-g", tip=f"sans bonus, {nom} km : {_pct(p)} ({n} personnes)")
    ax.ticks_x(list(range(len(tranches))), lambda v: tranches[int(v)][2], "kilomètres jusqu’au centre")
    _legende_traits(f, 228, [("m-line-b", "", "avec bonus"), ("m-line-gris", "5 3", "sans bonus")])
    return f.render()


def _barres_bras(titre_aria: str, bras: list[tuple[str, float, int]], hi: float, quoi: str,
                 temoin: tuple[int, ...] = (0,)) -> str:
    f = Fig(226, titre_aria)
    ax = Axes(f, 38, 24, W - 48, 140, -0.6, len(bras) - 0.4, 0, hi)
    ax.grid_y(_graduations(0, hi, 4), lambda v: _pct(v, 0), quoi)
    for k, (nom, p, n) in enumerate(bras):
        h = 1.96 * math.sqrt(p * (1 - p) / n)
        ax.bar(k, 0, p, 40, "m-bar2" if k in temoin else "m-bar", tip=f"{nom} : {_pct(p)} ({n})")
        ax.line([(k, max(p - h, 0)), (k, p + h)], "m-ci")
        for j, mot in enumerate(nom.split(" | ")):
            f.text(ax.sx(k), ax.y + ax.h + 14 + 13 * j, mot, "t-ax", "middle")
    return f.render()


@_fig("rondeau")
def m_rondeau() -> str:
    b = leviers.rondeau_bras()
    bras = [("objectif | 5 000 $", b["temoin_haut"][0], b["temoin_haut"][2]),
            ("objectif | 2 500 $", b["temoin_bas"][0], b["temoin_bas"][2]),
            ("premier don | annoncé", b["premier_don"][0], b["premier_don"][2]),
            ("doublement | promis", b["doublement"][0], b["doublement"][2])]
    hi = max(p + 1.96 * math.sqrt(p * (1 - p) / n) for _, p, n in bras) * 1.15
    return _barres_bras("Part des lettres suivies dun don selon la version tiree au sort, avec la marge "
                        "du hasard", bras, hi, "lettres suivies d’un don", temoin=(0, 1))


@_fig("defaut")
def m_defaut() -> str:
    R = synthese3.tous()
    a10, a11 = R["L10"].extra, R["L11"].extra
    bras = [("« non » | coché", a10["b"], a10["nb"]), ("« oui » | coché", a10["a"], a10["na"]),
            ("séance | simple", a11["b"], a11["nb"]), ("séance | détaillée", a11["a"], a11["na"])]
    return _barres_bras("Part des foyers qui souscrivent selon le choix coche davance et selon la seance, "
                        "avec la marge du hasard", bras, 0.7, "foyers qui souscrivent", temoin=(0, 2))


@_fig("blague")
def m_blague() -> str:
    g = leviers.gueguen_bras()
    bras = [("aucune | carte", g["aucune"][0], g["aucune"][1]),
            ("carte | publicitaire", g["publicite"][0], g["publicite"][1]),
            ("carte avec | une blague", g["blague"][0], g["blague"][1])]
    return _barres_bras("Part des clients qui laissent un pourboire selon la carte tiree au sort, avec la "
                        "marge du hasard", bras, 0.65, "clients qui laissent un pourboire", temoin=(0, 1))


@_fig("posture")
def m_posture() -> str:
    """Chaque table est un point : la dispersion se voit, pas seulement la moyenne."""
    L = leviers.donnees3.lynn()
    groupes = ((0, "debout"), (1, "accroupi"))
    vals = [r["pourboire"] / r["addition"] * 100 for r in L]
    hi = max(vals) * 1.08
    f = Fig(244, "Pourboire en part de laddition, table par table, serveur debout ou accroupi, avec "
                 "la moyenne de chaque groupe")
    ax = Axes(f, 38, 24, W - 48, 160, -0.6, 1.6, 0, hi)
    ax.grid_y(_graduations(0, hi, 4), lambda v: _num(v, 0) + " %", "pourboire, en part de l’addition")
    alea = stats.rng("posture-points")
    for k, nom in groupes:
        ys = [r["pourboire"] / r["addition"] * 100 for r in L if r["accroupi"] == k]
        for v in ys:
            ax.dot(k + (alea.random() - 0.5) * 0.5, v, "m-dot-b" if k else "m-dot-g", r=2.6,
                   tip=f"{nom} : {_num(v, 1)} % de l’addition")
        m = sum(ys) / len(ys)
        f.add(_marque("line", f'class="m-seuil" x1="{ax.sx(k - 0.38):.1f}" y1="{ax.sy(m):.1f}" '
                              f'x2="{ax.sx(k + 0.38):.1f}" y2="{ax.sy(m):.1f}"',
                      f"{nom}, moyenne : {_num(m, 1)} % ({len(ys)} tables)"))
        f.text(ax.sx(k), ax.y + ax.h + 15, nom, "t-lab", "middle")
        f.text(ax.sx(k), ax.y + ax.h + 29, f"moyenne {_num(m, 1)} %", "t-sub", "middle")
    return f.render()


@_fig("budget3")
def m_budget3() -> str:
    from .synthese import ENVOIS_SEMAINE
    items = []
    for i in synthese3.tous():
        b = synthese3.budget(i)
        if b is not None and synthese3.verdict(i) == "tient":
            items.append((i, b / ENVOIS_SEMAINE))
    items.sort(key=lambda t: t[1])
    rang = 34.0
    f = Fig(len(items) * rang + 58, "Semaines de test necessaires pour reverifier chaque levier etabli "
                                    "dans une agence")
    lo, hi = 0.05, max(s for _, s in items) * 1.8
    ax = Axes(f, 10, 18, W - 20, len(items) * rang, lo, hi, -0.5, len(items) - 0.5, xlog=True)
    graduations = [t for t in (0.1, 1, 10, 100, 1000) if lo <= t <= hi]
    for t in graduations:
        ax.vline(t, "m-grid")
    for k, (i, s) in enumerate(items):
        y = len(items) - 1 - k
        f.text(10, ax.sy(y) - 7, COURT[i], "t-lab")
        f.text(W - 10, ax.sy(y) - 7, f"{_num(s, 1)} sem.", "t-val", "end")
        ax.hbar(y - 0.16, lo, s, 7, "m-bar", tip=f"{i} {COURT[i]} : {_num(s, 1)} semaines")
    ax.ticks_x(graduations, lambda v: _num(v, 1 if v < 1 else 0), "semaines de test (échelle log)")
    return f.render()


@lru_cache(maxsize=1)
def rendre() -> dict[str, str]:
    return {k: f() for k, f in FIGURES.items()}
