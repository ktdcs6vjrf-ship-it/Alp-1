"""Les graphiques de la version mobile du cahier nº 2.

Mêmes règles et même boîte que `figmobile.py` (340 unités, aucune couleur
écrite en dur, domaines déduits des données, libellés ARIA sans apostrophe,
une valeur au toucher sur chaque marque) ; les outils de dessin en viennent.
"""

from __future__ import annotations

import math
from functools import lru_cache

from alp1.figterm import _num

from . import cibler, garder, objectif, registre2, relancer, stats, synthese2
from .figmobile import W, Axes, Fig, Scene, _cls, _graduations, _grille_iso, _legende, _marque, _pct

#: Nom court de chaque hypothèse du registre nº 2 (bulles, cartes, registre).
COURT = {
    "E01": "Courriel → achat", "E02": "Courriel → dépense", "E03": "Courriel → visite",
    "E04": "Courriel assorti", "E05": "Récence (courriel)", "E06": "Gros clients (courriel)",
    "E07": "Nouveaux (courriel)", "E08": "SMS → visite", "E09": "Déjà répondu",
    "E10": "Fréquents (SMS)", "E11": "Chasseurs de promos", "E12": "Hommes (SMS)",
    "E13": "SMS → achat", "E14": "Récence (SMS)", "E15": "Fréquents (SMS achat)",
    "E16": "Clients des promos",
    "C01": "Effet contre risque (courriel)", "C02": "Risque contre moyenne (courriel)",
    "C03": "Effet contre moyenne (courriel)", "C04": "Effet contre risque (Lenta)",
    "C05": "Risque contre moyenne (Lenta)", "C06": "Effet contre moyenne (Lenta)",
    "C07": "Effet contre risque (X5)", "C08": "Risque contre moyenne (X5)",
    "C09": "Effet contre moyenne (X5)",
    "G01": "BG/NBD contre rythme", "G02": "Fidèle silencieux", "G03": "Faille du modèle",
    "G04": "Décile de tête", "G05": "Première commande",
    "B01": "Juste au-dessus du but", "B02": "Campagne longue", "B03": "Objectif haut",
    "B04": "Objectif rond", "B05": "Lancement le week-end",
    "M01": "Passé → dépense (courriel)", "M02": "Passé → visite (Lenta)", "M03": "Passé → achat (X5)",
}

FIGURES: dict = {}

#: Les noms de famille en planche : « Fixer un objectif » sortait du cadre.
FAMILLE_COURTE = {**registre2.FAMILLES, "B": "Objectif"}


def _fig(cle: str):
    def deco(f):
        FIGURES[cle] = f
        return f
    return deco


def _pt(v: float, nd: int = 1) -> str:
    return ("+" if v >= 0 else "−") + _num(abs(v), nd) + " pt"


# ---------------------------------------------------------------------------
# La chasse
# ---------------------------------------------------------------------------

@_fig("chasse2")
def m_chasse2() -> str:
    res, q = synthese2.tous(), synthese2.q_valeurs()
    passes = [r.p for i, r in res.items() if q[i] < synthese2.SEUIL_Q]
    zbh = abs(stats.Phi_inv(max(passes) / 2))
    fams = list(registre2.FAMILLES)
    rang = 36.0
    f = Fig(len(fams) * rang + 64, "Les trente huit hypotheses placees selon leur z oriente, "
                                   "famille par famille, avec le seuil corrige")
    ax = Axes(f, 92, 22, W - 110, len(fams) * rang, -5, 12, -0.5, len(fams) - 0.5)
    ax.band([(-1.96, -0.5), (1.96, -0.5)], [(-1.96, len(fams) - 0.5), (1.96, len(fams) - 0.5)])
    ax.vline(0.0, "m-axis")
    ax.vline(zbh, "m-seuil")
    ax.vline(-zbh, "m-seuil")
    for k, fa in enumerate(fams):
        yrow = len(fams) - 1 - k
        f.text(ax.x - 8, ax.sy(yrow) + 4, FAMILLE_COURTE[fa], "t-lab", "end")
        ids = [i for i in res if i.startswith(fa)]
        for j, i in enumerate(ids):
            z = synthese2.z_oriente(i)
            v = synthese2.verdict(i)
            ax.dot(min(max(z, -5), 12), yrow + ((j % 3) - 1) * 0.17, _cls(v),
                   tip=f"{i} {COURT[i]} — z {_num(z, 1)}, {v}", r=4.2)
    ax.ticks_x([-4, 0, 4, 8, 12], lambda v: ("12+" if v == 12 else _num(v, 0)), "z orienté")
    return f.render()


@_fig("chasse2d")
def m_chasse2d() -> str:
    fams = list(registre2.FAMILLES)
    sc = Scene()
    pas, taille, unite = 30.0, 22.0, 6.0
    for k, fa in enumerate(fams):
        ids = [i for i in synthese2.tous() if i.startswith(fa)]
        t = sum(1 for i in ids if synthese2.verdict(i) == "tient")
        c = sum(1 for i in ids if synthese2.verdict(i) == "contraire")
        n = len(ids) - t - c
        z0 = 0.0
        for nb, tone, ghost, nom in ((t, "blue", False, "tiennent"), (c, "red", False, "contraires"),
                                     (n, "gray", True, "non établies")):
            if nb:
                sc.bloc(0, k * pas, taille, taille, nb * unite, tone, z=z0, ghost=ghost,
                        tip=f"{FAMILLE_COURTE[fa]} : {nb} {nom}")
                z0 += nb * unite
        sc.texte(taille, k * pas + taille / 2, 0, f"{FAMILLE_COURTE[fa]}  {t + c}/{len(ids)}",
                 "t-lab", "start", dx=10, dy=6)
    f = Fig(300, "Colonnes isometriques des hypotheses par famille, ce qui tient en bleu")
    bas = sc.rendre(f, 0, 0, W, 268)
    _legende(f, bas + 22, [("m-ok", "tient"), ("m-ko", "contraire"), ("m-nul", "non établi")])
    f.h = bas + 32
    return f.render()


# ---------------------------------------------------------------------------
# Le courriel (Hillstrom)
# ---------------------------------------------------------------------------

@_fig("courriel_bras")
def m_courriel_bras() -> str:
    bras = relancer.bras_hillstrom()
    f = Fig(214, "Taux de visite par bras du courriel tire au sort, avec intervalles")
    hi = max(v for _, v, _, _, _ in bras) * 1.18
    ax = Axes(f, 38, 24, W - 48, 140, -0.5, 2.5, 0, hi)
    ax.grid_y(_graduations(0, hi, 4), lambda v: _pct(v, 0), "ont visité le site")
    for k, (nom, v, a, d, n) in enumerate(bras):
        h = 1.96 * math.sqrt(v * (1 - v) / n)
        ax.bar(k, 0, v, 44, "m-bar2" if k == 0 else "m-bar",
               tip=f"courriel {nom} : {_pct(v)} de visites, {_pct(a, 2)} d’achats, "
                   f"{_num(d, 2)} $ par client ({n} clients)")
        ax.line([(k, v - h), (k, v + h)], "m-ci")
        f.text(ax.sx(k), ax.y + ax.h + 15, "aucun courriel" if k == 0 else f"courriel {nom}", "t-lab", "middle")
    return f.render()


@_fig("assorti")
def m_assorti() -> str:
    """Deux barres par groupe (le courriel de sa catégorie, l'autre) et un trait
    pour « aucun courriel » : trois aplats gris ne se distingueraient pas."""
    hs = relancer.donnees2.hillstrom()
    groupes = (("clients « hommes »", lambda r: r["hommes"] == 1 and r["femmes"] == 0, "h"),
               ("clients « femmes »", lambda r: r["hommes"] == 0 and r["femmes"] == 1, "f"))
    vals = []
    for nom, sel, bon in groupes:
        sub = [r for r in hs if sel(r)]
        trio = []
        for code in (bon, "f" if bon == "h" else "h", "0"):
            s = [r["visite"] for r in sub if r["courriel"] == code]
            trio.append((sum(s) / len(s), len(s)))
        vals.append((nom, trio))
    f = Fig(272, "Visites selon que le courriel parle de ce que le client achete deja ou de lautre "
                 "categorie, le trait marque le groupe sans courriel")
    hi = max(v for _, t in vals for v, _ in t) * 1.2
    ax = Axes(f, 38, 24, W - 48, 140, -0.6, 1.6, 0, hi)
    ax.grid_y(_graduations(0, hi, 4), lambda v: _pct(v, 0), "ont visité le site")
    for k, (nom, ((va, na), (vb, nb), (v0, n0))) in enumerate(vals):
        ax.bar(k - 0.19, 0, va, 34, "m-bar", tip=f"{nom}, courriel de sa catégorie : {_pct(va)} ({na} clients)")
        ax.bar(k + 0.19, 0, vb, 34, "m-bar2", tip=f"{nom}, l’autre courriel : {_pct(vb)} ({nb} clients)")
        y0 = ax.sy(v0)
        f.add(_marque("line", f'class="m-seuil" x1="{ax.sx(k - 0.45):.1f}" y1="{y0:.1f}" '
                              f'x2="{ax.sx(k + 0.45):.1f}" y2="{y0:.1f}"',
                      f"{nom}, aucun courriel : {_pct(v0)} ({n0} clients)"))
        f.text(ax.sx(k), ax.y + ax.h + 15, nom, "t-lab", "middle")
        # La valeur « aucun » sous l'axe : écrite sur le trait, elle barrait la barre grise.
        f.text(ax.sx(k), ax.y + ax.h + 30, f"sans courriel : {_pct(v0)}", "t-sub", "middle")
    _legende(f, 244, [("m-bar", "le courriel de sa catégorie"), ("m-bar2", "l’autre courriel")])
    f.text(0, 264, "pointillés : clients sans courriel", "t-sub")
    f.h = 272
    return f.render()


@_fig("courriel_iso")
def m_courriel_iso() -> str:
    z, rows, cols = relancer.grille_hillstrom("visite")
    sc, _, _ = _grille_iso(z, rows, cols, lambda v: _pt(v), "de visites avec le courriel",
                           taille=28, pas=36)
    f = Fig(300, "Blocs isometriques de leffet du courriel sur les visites selon la recence et la "
                 "depense de lannee")
    f.h = sc.rendre(f, 0, 0, W, 292) + 6
    return f.render()


# ---------------------------------------------------------------------------
# Le SMS (Lenta, X5)
# ---------------------------------------------------------------------------

@_fig("sms_reponse")
def m_sms_reponse() -> str:
    d = relancer.lenta_par_reponse()
    f = Fig(222, "Effet du SMS sur les visites selon la part de reponses aux SMS passes, avec "
                 "intervalles")
    lo = min(e - h for _, e, h, _ in d)
    hi = max(e + h for _, e, h, _ in d)
    lo, hi = min(lo, 0) * 1.1, hi * 1.1
    ax = Axes(f, 42, 24, W - 52, 150, -0.6, len(d) - 0.4, lo, hi)
    ax.grid_y(_graduations(lo, hi, 4), lambda v: _num(v, 0) + " pt", "effet du SMS sur les visites")
    ax.hline(0.0, "m-axis")
    for k, (nom, e, h, n) in enumerate(d):
        ax.bar(k, 0, e, 34, "m-bar" if e >= 0 else "m-bar-r",
               tip=f"réponses passées {nom} : {_pt(e, 2)} ({n} clients)")
        ax.line([(k, e - h), (k, e + h)], "m-ci")
        f.text(ax.sx(k), ax.y + ax.h + 15, nom, "t-lab", "middle")
    f.text(ax.x + ax.w, ax.y + ax.h + 30, "part de réponses aux SMS passés", "t-sub", "end")
    return f.render()


@_fig("sms_iso")
def m_sms_iso() -> str:
    z, rows, cols = relancer.grille_x5()
    sc, _, _ = _grille_iso(z, rows, cols, lambda v: _pt(v), "d’achats avec le SMS", taille=30, pas=38)
    f = Fig(300, "Blocs isometriques de leffet du SMS sur les achats selon la recence et la "
                 "frequence du client")
    f.h = sc.rendre(f, 0, 0, W, 292) + 6
    return f.render()


# ---------------------------------------------------------------------------
# Cibler
# ---------------------------------------------------------------------------

@_fig("ciblage")
def m_ciblage() -> str:
    eff = cibler.courbe("lenta", "effet", 10)
    ris = cibler.courbe("lenta", "risque", 10)
    tout = eff[-1][1]
    f = Fig(236, "Visites gagnees pour cent clients selon la part ecrite, rangee par effet estime, "
                 "par risque ou au hasard")
    hi = max(v for _, v in eff + ris) * 1.25
    ax = Axes(f, 40, 24, W - 68, 150, 0, 1, 0, hi)
    ax.grid_y(_graduations(0, hi, 4), lambda v: _num(v, 1), "visites gagnées pour 100 clients")
    ax.line([(0, 0), (1, tout)], "m-line-gris", "4 4")
    ax.line(ris, "m-line-r")
    ax.line(eff, "m-line-b")
    for (x, v), (_, w) in zip(eff[1:], ris[1:]):
        ax.dot(x, v, "m-dot-b", tip=f"{_num(x * 100, 0)} % écrits par effet : {_num(v, 2)} visites gagnées")
        ax.dot(x, w, "m-dot-r", tip=f"{_num(x * 100, 0)} % écrits par risque : {_num(w, 2)} visites gagnées")
    ax.ticks_x([0.25, 0.5, 0.75, 1], lambda v: _num(v * 100, 0) + " %", "part des clients écrits")
    _legende(f, 228, [("m-ok", "par effet estimé"), ("m-ko", "par risque"), ("m-nul", "au hasard")])
    f.h = 236
    return f.render()


@_fig("ciblage_iso")
def m_ciblage_iso() -> str:
    jeux = (("hillstrom", "Courriel"), ("lenta", "SMS Lenta"), ("x5", "SMS X5"))
    z = []
    for jeu, _ in jeux:
        T = cibler.tiers(jeu)
        moy = T["tous"][0]
        z.append([T["risque"][0] / moy, 1.0, T["effet"][0] / moy])
    sc, _, _ = _grille_iso(z, [n for _, n in jeux], ["par risque", "tous", "par effet"],
                           lambda v: "×" + _num(v, 2), "l’effet moyen", taille=30, pas=40)
    f = Fig(300, "Blocs isometriques de leffet du message dans le tiers choisi par risque, chez "
                 "tous, et dans le tiers choisi par effet, rapporte a leffet moyen")
    f.h = sc.rendre(f, 0, 0, W, 292) + 6
    return f.render()


# ---------------------------------------------------------------------------
# Garder (Online Retail II)
# ---------------------------------------------------------------------------

@_fig("garder_silence")
def m_garder_silence() -> str:
    par = garder.par_frequence(4)
    f = Fig(222, "Silencieux depuis six mois, jours dachat reels et predits lannee suivante selon "
                 "la frequence passee")
    hi = max(max(p, h) for _, p, h, _ in par) * 1.18
    ax = Axes(f, 30, 24, W - 40, 140, 0.4, len(par) + 0.6, 0, hi)
    ax.grid_y(_graduations(0, hi, 4), lambda v: _num(v, 1), "jours d’achat l’année suivante")
    for k, (nom, p, h, n) in enumerate(par, start=1):
        ax.bar(k - 0.17, 0, h, 15, "m-bar", tip=f"{nom} achats passés : {_num(h, 2)} réalisés ({n} clients)")
        ax.bar(k + 0.17, 0, p, 15, "m-bar2", tip=f"{nom} achats passés : {_num(p, 2)} prévus par le modèle")
        f.text(ax.sx(k), ax.y + ax.h + 14, nom, "t-ax", "middle")
    f.text(ax.x + ax.w, ax.y + ax.h + 29, "achats répétés avant le silence", "t-sub", "end")
    _legende(f, 214, [("m-bar", "réalisé"), ("m-bar2", "prévu par le modèle")])
    f.h = 222
    return f.render()


@_fig("garder_iso")
def m_garder_iso() -> str:
    z, rows, cols = garder.grille_premiere()
    sc, _, _ = _grille_iso(z, rows, cols, lambda v: _num(v, 1), "jours d’achat l’année suivante",
                           taille=28, pas=36)
    f = Fig(300, "Blocs isometriques des jours dachat de lannee suivante selon la premiere commande "
                 "et la frequence passee")
    f.h = sc.rendre(f, 0, 0, W, 292) + 6
    return f.render()


# ---------------------------------------------------------------------------
# L'objectif (Kickstarter)
# ---------------------------------------------------------------------------

@_fig("objectif_histo")
def m_objectif_histo() -> str:
    h = objectif.histogramme(0.8, 1.2, 0.02)
    f = Fig(214, "Campagnes par tranche de lobjectif atteint, de 80 a 120 pour cent, en echelle "
                 "logarithmique, le mur a 100")
    # En échelle linéaire, les tranches sous l'objectif (quelques dizaines de
    # campagnes) disparaissaient sous le mur de dix-neuf mille : le vide se lit en log.
    mx = max(n for _, n in h) * 1.6
    ax = Axes(f, 48, 24, W - 58, 140, 0.8, 1.2, 10, mx, ylog=True)
    ax.grid_y([t for t in (10, 100, 1000, 10000) if t <= mx], lambda v: _num(v, 0), "campagnes (échelle log)")
    for a, n in h:
        cls = "m-bar" if a >= 1.0 - 1e-9 else "m-bar-pale"
        ax.bar(a + 0.01, 10, max(n, 10), 5.6, cls,
               tip=f"de {_num(a * 100, 0)} à {_num((a + 0.02) * 100, 0)} % : {n} campagnes")
    ax.vline(1.0, "m-seuil")
    ax.ticks_x([0.9, 1.0, 1.1], lambda v: _num(v * 100, 0) + " %", "part de l’objectif atteinte")
    return f.render()


@_fig("objectif_iso")
def m_objectif_iso() -> str:
    z, rows, cols = objectif.reussite_duree_objectif()
    sc, _, _ = _grille_iso(z, rows, cols, lambda v: _num(v, 0) + " %", "de réussite", taille=26, pas=33)
    f = Fig(300, "Blocs isometriques du taux de reussite selon la duree de la campagne et son objectif")
    f.h = sc.rendre(f, 0, 0, W, 292) + 6
    return f.render()


# ---------------------------------------------------------------------------
# Mesurer
# ---------------------------------------------------------------------------

@_fig("cuped")
def m_cuped() -> str:
    R = synthese2.tous()
    items = (("M01", "Courriel, dépense sur 2 semaines"), ("M02", "SMS Lenta, visite"),
             ("M03", "SMS X5, achat"))
    rang = 46.0
    f = Fig(len(items) * rang + 52, "Part de la variance retiree par lhistorique du client, "
                                    "trois experiences")
    hi = max(R[i].extra["r2"] for i, _ in items) * 100 * 1.25
    ax = Axes(f, 10, 18, W - 20, len(items) * rang, 0, hi, -0.5, len(items) - 0.5)
    for k, (i, nom) in enumerate(items):
        y = len(items) - 1 - k
        v = R[i].extra["r2"] * 100
        f.text(10, ax.sy(y) - 9, nom, "t-lab")
        f.text(W - 10, ax.sy(y) - 9, _num(v, 1) + " %", "t-val", "end")
        ax.hbar(y - 0.12, 0, v, 9, "m-bar", tip=f"{nom} : {_num(v, 1)} % d’envois en moins")
    ax.ticks_x(_graduations(0, hi, 4), lambda v: _num(v, 0) + " %", "envois économisés")
    return f.render()


@_fig("budget2")
def m_budget2() -> str:
    from .synthese import ENVOIS_SEMAINE
    items = []
    for i in synthese2.tous():
        b = synthese2.budget(i)
        if b is not None and synthese2.verdict(i) == "tient":
            items.append((i, b / ENVOIS_SEMAINE))
    items.sort(key=lambda t: t[1])
    rang = 30.0
    f = Fig(len(items) * rang + 58, "Semaines de test necessaires pour reverifier chaque effet "
                                    "etabli dans une agence")
    lo, hi = 0.05, max(s for _, s in items) * 1.6
    ax = Axes(f, 10, 18, W - 20, len(items) * rang, lo, hi, -0.5, len(items) - 0.5, xlog=True)
    graduations = [t for t in (0.1, 1, 10, 100, 1000) if lo <= t <= hi]
    for t in graduations:
        ax.vline(t, "m-grid")
    for k, (i, s) in enumerate(items):
        y = len(items) - 1 - k
        f.text(10, ax.sy(y) - 6, COURT[i], "t-lab")
        f.text(W - 10, ax.sy(y) - 6, f"{_num(s, 1)} sem.", "t-val", "end")
        ax.hbar(y - 0.18, lo, s, 7, "m-bar", tip=f"{i} {COURT[i]} : {_num(s, 1)} semaines")
    ax.ticks_x(graduations, lambda v: _num(v, 1 if v < 1 else 0), "semaines de test (échelle log)")
    return f.render()


@lru_cache(maxsize=1)
def rendre() -> dict[str, str]:
    return {k: f() for k, f in FIGURES.items()}
