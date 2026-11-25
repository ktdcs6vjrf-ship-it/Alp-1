"""Les graphiques de la version mobile du cahier nº 4.

Mêmes règles et même boîte que les cahiers nº 1 à 3 (340 unités, aucune couleur
écrite en dur, domaines déduits des données, libellés ARIA sans apostrophe, une
valeur au toucher sur chaque marque). Le bleu marque ce qui passe ou ce qui
tient, le rouge ce qui échoue ou contredit, le gris ce qui reste dans le bruit
ou ne s'applique pas.
"""

from __future__ import annotations

import math
from functools import lru_cache

from alp1.figterm import _num

from . import arene, calcul4, litterature4, synthese4
from . import registre4 as R4
from .etalonnage4 import lire as etalonnage
from .figmobile import W, Axes, Fig, Scene, _graduations, _grille_iso, _legende

FIGURES: dict = {}

MARCHE = {"hillstrom": "Hillstrom", "lenta": "Lenta", "x5": "X5", "cdnow": "CDNOW", "retail": "Retail"}
REGLE = {"appris": "Appris chez soi", "valeur": "Gros dépensiers", "risque": "Plus à risque", "hasard": "Hasard"}
CLASSE = {"appris": "m-bar", "valeur": "m-blanc", "risque": "m-bar2", "hasard": "m-bar-nuit"}

COURT = {
    "A01": "Contre les gros dépensiers · Hillstrom", "A02": "Contre les gros dépensiers · Lenta",
    "A03": "Contre les gros dépensiers · X5", "A04": "Contre les plus à risque · Hillstrom",
    "A05": "Contre les plus à risque · Lenta", "A06": "Contre les plus à risque · X5",
    "A07": "Contre le hasard · Hillstrom", "A08": "Contre le hasard · Lenta", "A09": "Contre le hasard · X5",
    "A10": "La mode contre le hasard · Hillstrom", "A11": "La mode contre le hasard · Lenta",
    "A12": "La mode contre le hasard · X5",
    "B01": "Thompson · tous les articles", "B02": "Thompson · hommes", "B03": "Thompson · femmes",
    "B04": "Thompson · trois rayons", "K01": "La foule de la catégorie", "K02": "Sa catégorie ou tout le site",
    "K03": "Les pionniers d’un pays", "W01": "Baleines · CDNOW", "W02": "Baleines · Retail", "W03": "Baleines · X5",
    "R01": "Accélération · CDNOW", "R02": "Accélération · Retail", "R03": "Accélération · X5",
}


def _fig(cle: str):
    def deco(f):
        FIGURES[cle] = f
        return f
    return deco


def _pt(v: float, nd: int = 2) -> str:
    return ("+" if v >= 0 else "−") + _num(abs(v), nd)


def _pct(v: float, nd: int = 0) -> str:
    return _num(v * 100, nd) + " %"


def _seg(ax: Axes, x0, y0, x1, y1, cls: str) -> None:
    ax.line([(x0, y0), (x1, y1)], cls)


# ---------------------------------------------------------------------------
# Le marché
# ---------------------------------------------------------------------------

@_fig("marche")
def m_marche() -> str:
    c = litterature4.CHIFFRES
    rows = [("Paiements des fans", c["croissance_brut"]), ("Comptes de créateurs", c["croissance_createurs"]),
            ("Comptes de fans", c["croissance_fans"])]
    f = Fig(150, "Croissance sur un an des paiements des fans, des comptes de createurs et des comptes de fans")
    hi = max(v for _, v in rows) * 1.15
    ax = Axes(f, 150, 14, W - 190, 3 * 34, 0, hi, -0.5, 2.5)
    for k, (nom, v) in enumerate(rows):
        y = 2 - k
        ax.hbar(y, 0, v, 18, "m-bar" if k == 0 else "m-bar2", tip=f"{nom} : +{_pct(v)} en un an")
        f.text(ax.x - 8, ax.sy(y) + 4, nom, "t-lab", "end")
        f.text(ax.sx(v) + 6, ax.sy(y) + 4, "+" + _pct(v), "t-val")
    ax.ticks_x(_graduations(0, hi, 3), lambda t: _pct(t), "croissance 2023 → 2024")
    return f.render()


@_fig("argent3d")
def m_argent3d() -> str:
    """Sur 100 $ payés par les fans : la plateforme, la créatrice, le chat, et ce qui reste à l'agence."""
    plateforme = R4.PLATEFORME * 100
    sc = Scene()
    pas, taille = 40.0, 26.0
    for k, (niveau, nom) in enumerate(R4.STRATEGIES.items()):
        prise = R4.PRISE[niveau]
        chat = R4.COUT_HUMAIN * 100
        agence = prise * (100 - plateforme) - chat
        creatrice = (1 - prise) * (100 - plateforme)
        z0 = 0.0
        for v, tone, quoi in ((plateforme, "gray", "plateforme"), (creatrice, "sky", "créatrice"),
                              (chat, "pale", "chat"), (agence, "blue", "agence")):
            sc.bloc(0, k * pas, taille, taille, v * 1.3, tone, z=z0, tip=f"{nom} : {_num(v, 0)} $ pour {quoi}")
            z0 += v * 1.3
        sc.texte(taille, k * pas + taille / 2, 0, f"{nom} · {_num(agence, 0)} $", "t-lab", "start", dx=10, dy=6)
    f = Fig(330, "Repartition de cent dollars payes par les fans selon la strategie de l agence")
    bas = sc.rendre(f, 0, 0, W, 290)
    _legende(f, bas + 22, [("m-bar2", "plateforme"), ("m-bar-nuit", "créatrice"), ("m-bar-pale", "chat"),
                           ("m-bar", "agence")])
    f.h = bas + 32
    return f.render()


@_fig("niveaux")
def m_niveaux() -> str:
    tau = litterature4.CHIFFRES["tau"]
    p = [math.exp(-tau) * tau ** k / math.factorial(k) for k in range(3)]
    p.append(1 - sum(p))
    noms = list(R4.STRATEGIES.values())
    f = Fig(220, "Part des gens a chaque niveau de raisonnement selon le modele de Camerer Ho et Chong")
    hi = max(p) * 1.25
    ax = Axes(f, 34, 22, W - 44, 140, -0.5, 3.5, 0, hi)
    ax.grid_y(_graduations(0, hi, 3), lambda t: _pct(t), "part des gens")
    for k, v in enumerate(p):
        ax.bar(k, 0, v, 46, "m-bar" if k == 2 else "m-bar2", tip=f"Niveau {k} ({noms[k]}) : {_pct(v)}")
        f.text(ax.sx(k), ax.sy(v) - 6, _pct(v), "t-val", "middle")
    for k, nom in enumerate(noms):
        f.text(ax.sx(k), ax.y + ax.h + 15, f"niveau {k}" + ("+" if k == 3 else ""), "t-ax", "middle")
        f.text(ax.sx(k), ax.y + ax.h + 30, nom.replace("Un coup", "1 coup"), "t-sub", "middle")
    return f.render()


# ---------------------------------------------------------------------------
# Famille A
# ---------------------------------------------------------------------------

@_fig("a_gains")
def m_a_gains() -> str:
    jeux = ("hillstrom", "lenta", "x5")
    G = calcul4.charger()["gains"]
    haut = 96.0
    f = Fig(len(jeux) * (haut + 40) + 34, "Gain du message pour cent clients selon la politique sur trois marches")
    y = 18.0
    for jeu in jeux:
        gains = G[jeu]
        hi = max(gains.values()) * 1.2
        lo = min(0.0, min(gains.values()) * 1.2)
        ax = Axes(f, 40, y + 14, W - 50, haut, -0.5, 3.5, lo, hi)
        f.text(0, y + 4, MARCHE[jeu], "t-lab")
        ax.grid_y(_graduations(lo, hi, 2), lambda t: _num(t, 1))
        for k, r in enumerate(("appris", "valeur", "risque", "hasard")):
            ax.bar(k, 0, gains[r], 40, CLASSE[r], tip=f"{MARCHE[jeu]} · {REGLE[r]} : {_pt(gains[r])} pour 100 clients")
            f.text(ax.sx(k), ax.sy(max(gains[r], 0)) - 5, _pt(gains[r]), "t-val", "middle")
        ax.hline(0, "m-axis")
        y += haut + 40
    _legende(f, y + 2, [(CLASSE[r], REGLE[r]) for r in ("appris", "valeur", "risque", "hasard")])
    f.h = y + 30
    return f.render()


@_fig("a_spec3d")
def m_a_spec3d() -> str:
    """X5 : écart appris − hasard (points pour 100 clients) selon le pilote et la part écrite (modèle mco)."""
    b = synthese4.batteries()["A09"]
    val = {tuple(nom): d for (d, _), nom in zip(b["spec"], b["spec_noms"])}
    z = [[val[(p, bu, "mco")] for bu in R4.BUDGETS] for p in R4.PILOTES]
    rows = [f"pilote {_num(p * 100, 0)} %" for p in R4.PILOTES]
    cols = [f"{_num(bu * 100, 0)} %" for bu in R4.BUDGETS]
    sc, lo, hi = _grille_iso(z, rows, cols, lambda v: _pt(v), "pour 100 clients")
    f = Fig(300, "Blocs isometriques de l ecart entre la politique apprise et le hasard selon le pilote et la part ecrite")
    bas = sc.rendre(f, 0, 0, W, 270)
    f.text(0, bas + 20, f"de {_pt(lo)} à {_pt(hi)} pour 100 clients · X5", "t-sub")
    f.h = bas + 28
    return f.render()


@_fig("a_spec")
def m_a_spec() -> str:
    ids = ("A07", "A08", "A09")
    haut = 70.0
    f = Fig(len(ids) * (haut + 34) + 36, "Courbe de specification des trente six reglages contre le hasard sur trois marches")
    y = 16.0
    for i in ids:
        b = synthese4.batteries()[i]
        pts = sorted(tuple(x) for x in b["spec"])
        lo = min(0.0, min(d for d, _ in pts)) * 1.15
        hi = max(d for d, _ in pts) * 1.15
        ax = Axes(f, 40, y + 12, W - 50, haut, -0.5, len(pts) - 0.5, lo, hi)
        f.text(0, y + 2, MARCHE[R4.par_id()[i].jeu], "t-lab")
        ax.grid_y(_graduations(lo, hi, 2), lambda t: _num(t, 1))
        ax.hline(0, "m-axis")
        for k, (d, p) in enumerate(pts):
            cls = "m-dot-b" if (p < 0.05 and d > 0) else ("m-dot-r" if (p < 0.05 and d < 0) else "m-dot-g")
            ax.dot(k, d, cls, tip=f"{MARCHE[R4.par_id()[i].jeu]} : réglage {k + 1}, {_pt(d)} pour 100 clients", r=2.8)
        y += haut + 34
    _legende(f, y, [("m-ok", "significatif, dans le sens"), ("m-nul", "dans le bruit"), ("m-ko", "significatif, à l’envers")])
    f.h = y + 12
    return f.render()


# ---------------------------------------------------------------------------
# La batterie
# ---------------------------------------------------------------------------

@_fig("batterie")
def m_batterie() -> str:
    ids = list(synthese4.tous())
    tests = [t for t, _, _ in R4.TESTS]
    cel, gauche, haut = 17.0, 44.0, 13.0
    f = Fig(len(ids) * haut + 58, "Grille des vingt cinq hypotheses et des treize tests, bleu passe, rouge echoue")
    for j, t in enumerate(tests):
        f.text(gauche + j * cel + cel / 2, 12, str(j + 1), "t-ax", "middle")
    f.text(gauche + len(tests) * cel + 14, 12, "✓", "t-ax", "middle")
    for k, i in enumerate(ids):
        b = synthese4.bilan(i)
        y = 20 + k * haut
        f.text(gauche - 6, y + 10, i, "t-ax", "end")
        for j, t in enumerate(tests):
            etat = b["tests"][t]["etat"]
            cls = {"passe": "m-ok", "echoue": "m-ko", "sans objet": "m-band"}[etat]
            tip = f"{i} · {R4.TESTS[j][1]} : {etat}" + (f" ({b['tests'][t]['detail']})" if b["tests"][t]["detail"] else "")
            f.add(f'<rect class="{cls}" x="{gauche + j * cel + 1.5:.1f}" y="{y + 1.5:.1f}" width="{cel - 3:.1f}" '
                  f'height="{haut - 3:.1f}" rx="2.5" data-tip="{tip.replace(chr(39), chr(8217))}" tabindex="0">'
                  f'<title>{tip.replace(chr(39), chr(8217))}</title></rect>')
        x = gauche + len(tests) * cel + 14
        f.add(f'<circle class="{"m-dot-b" if b["survit"] else "m-dot-g"}" cx="{x:.1f}" cy="{y + haut / 2:.1f}" r="4"/>')
    _legende(f, 20 + len(ids) * haut + 22, [("m-ok", "passe"), ("m-ko", "échoue"), ("m-band", "sans objet")])
    return f.render()


@_fig("batterie3d")
def m_batterie3d() -> str:
    fams = list(R4.FAMILLES)
    sc = Scene()
    pas, taille, unite = 34.0, 22.0, 2.6
    for k, fa in enumerate(fams):
        ids = [i for i in synthese4.tous() if i.startswith(fa)]
        etats = [synthese4.bilan(i)["tests"][t]["etat"] for i in ids for t, _, _ in R4.TESTS]
        z0 = 0.0
        for etat, tone, ghost in (("passe", "blue", False), ("echoue", "red", False), ("sans objet", "gray", True)):
            nb = etats.count(etat)
            if nb:
                sc.bloc(0, k * pas, taille, taille, nb * unite, tone, z=z0, ghost=ghost, tip=f"{R4.FAMILLES[fa]} : {nb} {etat}")
                z0 += nb * unite
        surv = sum(1 for i in ids if synthese4.bilan(i)["survit"])
        sc.texte(taille, k * pas + taille / 2, 0, f"{R4.FAMILLES[fa]} · {surv}/{len(ids)}", "t-lab", "start", dx=10, dy=6)
    f = Fig(330, "Colonnes isometriques des tests passes et echoues par famille")
    bas = sc.rendre(f, 0, 0, W, 296)
    _legende(f, bas + 22, [("m-ok", "passe"), ("m-ko", "échoue"), ("m-nul", "sans objet")])
    f.h = bas + 32
    return f.render()


# ---------------------------------------------------------------------------
# B, K, W, R
# ---------------------------------------------------------------------------

@_fig("b_jours")
def m_b_jours() -> str:
    m = synthese4.batteries()["B04"]
    vals = m["par_jour"]
    c = litterature4.CHIFFRES
    ref = (c["obp_thompson"] - c["obp_hasard"]) * 100
    lo = min(0.0, min(vals)) * 1.25
    hi = max(max(vals), ref) * 1.25
    f = Fig(220, "Ecart de clics entre Thompson et le hasard jour par jour sur la semaine du test")
    ax = Axes(f, 44, 22, W - 54, 150, -0.5, len(vals) - 0.5, lo, hi)
    ax.grid_y(_graduations(lo, hi, 3), lambda t: _num(t, 2), "point de clic, Thompson moins hasard")
    for k, v in enumerate(vals):
        ax.bar(k, 0, v, 26, "m-bar" if v > 0 else "m-bar-r", tip=f"{m['jours'][k]} : {_pt(v)} point")
        f.text(ax.sx(k), ax.y + ax.h + 14, m["jours"][k][8:10] + " nov.", "t-ax", "middle")
    ax.hline(0, "m-axis")
    ax.hline(ref, "m-seuil")
    f.text(ax.x + ax.w, ax.sy(ref) - 5, f"jeu complet : {_pt(ref)} (article)", "t-sub", "end")
    return f.render()


@_fig("k_annees")
def m_k_annees() -> str:
    b = synthese4.batteries()["K01"]
    vals, noms = b["temps"], b["temps_noms"]
    lo = min(0.0, min(vals)) * 1.2
    hi = max(0.0, max(vals)) * 1.2
    f = Fig(210, "Pente de la reussite selon la foule de la categorie annee par annee")
    ax = Axes(f, 40, 22, W - 50, 140, -0.5, len(vals) - 0.5, lo, hi)
    ax.grid_y(_graduations(lo, hi, 3), lambda t: _num(t, 0), "points par unité de log de la foule")
    for k, v in enumerate(vals):
        ax.bar(k, 0, v, 22, "m-bar" if v < 0 else "m-bar2", tip=f"{noms[k]} : {_pt(v, 1)} point")
        f.text(ax.sx(k), ax.y + ax.h + 14, str(noms[k])[2:], "t-ax", "middle")
    ax.hline(0, "m-axis")
    f.text(ax.x + ax.w, ax.y + ax.h + 29, "année de lancement (20…)", "t-sub", "end")
    return f.render()


@_fig("k_pionniers")
def m_k_pionniers() -> str:
    c = calcul4.charger()["k03"]
    pl = calcul4.charger()["k03_placebo"]
    vals = []
    for pays, e, l_, E, L in c["cellules"]:
        vals.append((100 * ((e[1] / e[0] - l_[1] / l_[0]) - (E[1] / E[0] - L[1] / L[0])), pays, e[0]))
    vals.sort()
    lo = min(v for v, *_ in vals) * 1.1
    hi = max(v for v, *_ in vals) * 1.1
    f = Fig(250, "Ecart pionniers moins suivants par pays avec le vrai jour d ouverture et un faux jour un an plus tard")
    ax = Axes(f, 40, 22, W - 50, 170, -0.5, len(vals) - 0.5, lo, hi)
    ax.grid_y(_graduations(lo, hi, 3), lambda t: _num(t, 0), "points de réussite, témoin américain retiré")
    ax.hline(0, "m-axis")
    for k, (v, pays, n) in enumerate(vals):
        ax.dot(k, v, "m-dot-g", tip=f"{pays} : {_pt(v, 1)} point ({n} pionnières)", r=3.2)
        f.text(ax.sx(k), ax.y + ax.h + 13, pays, "t-ax", "middle")
    ax.hline(c["d"], "m-line-b")
    ax.hline(pl["d"], "m-line-r")
    f.text(ax.x + 2, ax.sy(c["d"]) - 5, f"vraie ouverture {_pt(c['d'], 1)}", "t-sub")
    f.text(ax.x + ax.w, ax.sy(pl["d"]) + 13, f"fausse ouverture {_pt(pl['d'], 1)}", "t-sub", "end")
    return f.render()


@_fig("w_baleines")
def m_w_baleines() -> str:
    jeux = ("cdnow", "retail", "x5")
    B = calcul4.charger()["baleines"]
    f = Fig(150, "Part des baleines de demain qui etaient deja baleines sur trois marches")
    ax = Axes(f, 70, 10, W - 82, 3 * 32, 0, 1, -0.5, 2.5)
    for k, jeu in enumerate(jeux):
        m = B[jeu][str(R4.BALEINE)]
        y = 2 - k
        deja = 1 - m["part"]
        ax.hbar(y, 0, deja, 18, "m-bar", tip=f"{MARCHE[jeu]} : {_pct(deja)} étaient déjà baleines")
        ax.hbar(y, deja, 1, 18, "m-bar2", tip=f"{MARCHE[jeu]} : {_pct(m['part'])} sont nouvelles")
        f.text(ax.x - 8, ax.sy(y) + 4, MARCHE[jeu], "t-lab", "end")
        f.text(ax.sx(deja) - 6, ax.sy(y) + 4, _pct(deja), "t-val", "end")
    ax.vline(0.5, "m-seuil")
    ax.ticks_x([0, 0.25, 0.5, 0.75, 1], lambda t: _pct(t), "part des baleines de la validation")
    _legende(f, 146, [("m-bar", "déjà baleines"), ("m-bar2", "nouvelles")])
    f.h = 158
    return f.render()


@_fig("w3d")
def m_w3d() -> str:
    jeux = ("cdnow", "retail", "x5")
    B = calcul4.charger()["baleines"]
    z = [[1 - B[j][str(q)]["part"] for q in R4.W_PARTS] for j in jeux]
    sc, lo, hi = _grille_iso(z, [MARCHE[j] for j in jeux], [f"tête {_num(q * 100, 1)} %" for q in R4.W_PARTS],
                             lambda v: _pct(v), "déjà baleines")
    f = Fig(290, "Blocs isometriques de la part des baleines qui l etaient deja selon le marche et la taille de la tete")
    bas = sc.rendre(f, 0, 0, W, 262)
    f.text(0, bas + 20, f"de {_pct(lo)} à {_pct(hi)} déjà baleines", "t-sub")
    f.h = bas + 28
    return f.render()


@_fig("r_glissant")
def m_r_glissant() -> str:
    series = calcul4.charger()["r_temps"]
    allv = [v for s in series.values() for v in s["serie"]]
    hi = max(allv) * 1.25
    f = Fig(220, "Effet de l acceleration au dela de RFM a sept coupes successives sur deux marches")
    n = len(series["cdnow"]["serie"])
    ax = Axes(f, 44, 22, W - 54, 150, -0.3, n - 0.7, 0, hi)
    ax.grid_y(_graduations(0, hi, 3), lambda t: _num(t, 2), "IC partiel au-delà de RFM")
    for jeu, cls, dot in (("cdnow", "m-line-b", "m-dot-b"), ("retail", "m-line", "m-dot")):
        s = series[jeu]["serie"]
        ax.line(list(enumerate(s)), cls)
        for k, v in enumerate(s):
            ax.dot(k, v, dot, tip=f"{MARCHE[jeu]}, coupe du {series[jeu]['noms'][k]} : {_pt(v, 3)}", r=3)
    for k, nom in enumerate(series["cdnow"]["noms"]):
        f.text(ax.sx(k), ax.y + ax.h + 14, str(k + 1), "t-ax", "middle")
    f.text(ax.x + ax.w, ax.y + ax.h + 29, "coupe (de la plus ancienne à la plus récente)", "t-sub", "end")
    _legende(f, 214, [("m-bar", "CDNOW"), ("m-blanc", "Retail")])
    f.h = 224
    return f.render()


@_fig("r3d")
def m_r3d() -> str:
    jeux = ("cdnow", "retail", "x5")
    z = []
    for jeu in jeux:
        b = synthese4.batteries()[{"cdnow": "R01", "retail": "R02", "x5": "R03"}[jeu]]
        val = {tuple(nom): d for (d, _), nom in zip(b["spec"], b["spec_noms"])}
        z.append([max(val[(d, 3, "depense")], 1e-6) for d in R4.R_DEFINITIONS])
    noms = {"moities": "moitiés", "tiers": "tiers", "dernier": "dernier écart"}
    sc, lo, hi = _grille_iso(z, [MARCHE[j] for j in jeux], [noms[d] for d in R4.R_DEFINITIONS],
                             lambda v: _pt(v, 3), "d’IC partiel")
    f = Fig(280, "Blocs isometriques de l effet de l acceleration selon le marche et sa definition")
    bas = sc.rendre(f, 0, 0, W, 252)
    f.text(0, bas + 20, f"de {_pt(lo, 3)} à {_pt(hi, 3)} d’IC partiel, toujours positif", "t-sub")
    f.h = bas + 28
    return f.render()


# ---------------------------------------------------------------------------
# L'arène
# ---------------------------------------------------------------------------

@_fig("arene_rangs")
def m_arene_rangs() -> str:
    j = calcul4.charger()["arene"]["jouer"]
    f = Fig(200, "Rang final de l agence selon sa strategie sur quatre cents tirages de l arene")
    ax = Axes(f, 120, 10, W - 132, 4 * 34, 0, 1, -0.5, 3.5)
    for k, (s, nom) in enumerate(R4.STRATEGIES.items()):
        r = sorted(t[s]["rang"] for t in j)
        q1, q2, q3 = r[len(r) // 4], r[len(r) // 2], r[3 * len(r) // 4]
        y = 3 - k
        _seg(ax, r[0], y, r[-1], y, "m-ci")
        ax.hbar(y, q1, q3, 14, "m-bar" if s == 2 else "m-bar2", tip=f"{nom} : la moitié des tirages entre {_pct(q1)} et {_pct(q3)}")
        ax.dot(q2, y, "m-dot", tip=f"{nom} : rang médian {_pct(q2)}", r=3.6)
        f.text(ax.x - 8, ax.sy(y) + 4, nom, "t-lab", "end")
    ax.ticks_x([0, 0.25, 0.5, 0.75, 1], lambda t: _pct(t), "part des agences dépassées à 36 mois")
    return f.render()


def _influents() -> list[tuple[str, float, float]]:
    out = []
    for p in R4.DOMAINE:
        s = calcul4.charger()["arene"]["sensibilite"][p]
        out.append((p, s[0][1], s[-1][1]))
    out.sort(key=lambda x: -abs(x[2] - x[1]))
    return out


NOM_PARAM = {
    "tau": "coups d’avance de la foule", "imitation": "vitesse d’imitation", "capacite": "facilité à copier",
    "encombrement": "usure par la foule", "divulgation": "perte si l’IA s’annonce", "part_chat": "part du chat",
    "economie_ia": "économie de l’IA", "controle": "chance de contrôle", "bascule": "délai pour repasser à l’humain",
    "temoin": "taille du témoin", "apprentissage": "fans pour apprendre", "depart": "départs des créatrices",
    "sensibilite": "départs selon la prise", "attrait": "attrait de la paie", "visibilite": "avantage de taille",
    "bruit": "bruit du revenu", "heterogeneite": "écart de taille au départ", "transparence": "coût de la franchise",
}


@_fig("arene_tornade")
def m_arene_tornade() -> str:
    top = _influents()[:8]
    f = Fig(len(top) * 26 + 56, "Part des tirages ou un coup d avance bat la mode quand chaque parametre est bas ou haut")
    ax = Axes(f, 150, 10, W - 160, len(top) * 26, 0, 1, -0.5, len(top) - 0.5)
    for k, (p, bas, haut) in enumerate(top):
        y = len(top) - 1 - k
        _seg(ax, bas, y, haut, y, "m-ci")
        ax.dot(bas, y, "m-dot-g", tip=f"{NOM_PARAM[p]} bas : {_pct(bas)} des tirages", r=3.6)
        ax.dot(haut, y, "m-dot-b", tip=f"{NOM_PARAM[p]} haut : {_pct(haut)} des tirages", r=3.6)
        f.text(ax.x - 8, ax.sy(y) + 4, NOM_PARAM[p], "t-ax", "end")
    ax.vline(R4.SEUIL_ARENE, "m-seuil")
    ax.ticks_x([0, 0.25, 0.5, 0.75, 1], lambda t: _pct(t), "tirages où le niveau 2 bat la mode")
    _legende(f, len(top) * 26 + 50, [("m-nul", "paramètre bas"), ("m-ok", "paramètre haut")])
    f.h = len(top) * 26 + 60
    return f.render()


@_fig("arene3d")
def m_arene3d() -> str:
    (p1, *_), (p2, *_) = _influents()[:2]
    j, th = calcul4.charger()["arene"]["jouer"], arene.tirages()
    k = 5
    z = [[0.0] * k for _ in range(k)]
    n = [[0] * k for _ in range(k)]
    lo1, hi1 = R4.DOMAINE[p1]
    lo2, hi2 = R4.DOMAINE[p2]
    for i, t in enumerate(j):
        a = min(k - 1, int((th[i][p1] - lo1) / (hi1 - lo1) * k))
        b = min(k - 1, int((th[i][p2] - lo2) / (hi2 - lo2) * k))
        n[a][b] += 1
        z[a][b] += t[2]["rang"] > t[1]["rang"]
    z = [[max(z[a][b] / n[a][b], 0.02) if n[a][b] else 0.02 for b in range(k)] for a in range(k)]
    rows = [f"{NOM_PARAM[p1]} {q + 1}/5" if q in (0, k - 1) else "" for q in range(k)]
    cols = [f"{q + 1}/5" for q in range(k)]
    sc, lo, hi = _grille_iso(z, rows, cols, lambda v: _pct(v), "des tirages")
    f = Fig(300, "Blocs isometriques de la part des tirages ou le niveau deux bat la mode selon les deux parametres les plus influents")
    bas = sc.rendre(f, 0, 0, W, 262)
    f.text(0, bas + 18, f"colonnes : {NOM_PARAM[p2]}, du plus bas (1/5) au plus haut (5/5)", "t-sub")
    f.h = bas + 26
    return f.render()


@_fig("arene_part")
def m_arene_part() -> str:
    j = calcul4.charger()["arene"]["jouer"]
    pts = []
    for s, nom in R4.STRATEGIES.items():
        parts = sorted(t[s]["part"] for t in j)
        rangs = sorted(t[s]["rang"] for t in j)
        pts.append((parts[len(parts) // 2], rangs[len(rangs) // 2], nom, s))
    hx = max(p for p, *_ in pts) * 1.3
    f = Fig(230, "Part des creatrices captee et rang de profit median pour chaque strategie")
    ax = Axes(f, 44, 16, W - 60, 160, 0, hx, 0.3, 0.7)
    ax.grid_y([0.3, 0.4, 0.5, 0.6, 0.7], lambda t: _pct(t), "rang de profit médian")
    for p, r, nom, s in pts:
        ax.dot(p, r, "m-dot-b" if s == 2 else "m-dot", tip=f"{nom} : {_pct(p, 2)} des créatrices, rang {_pct(r)}", r=5)
        f.text(ax.sx(p) + 8, ax.sy(r) + 4, nom, "t-lab")
    ax.ticks_x(_graduations(0, hx, 3), lambda t: _pct(t, 2), "part des créatrices à 36 mois (médiane)")
    return f.render()


# ---------------------------------------------------------------------------
# Étalonnage et recoupement
# ---------------------------------------------------------------------------

@_fig("etalonnage")
def m_etalonnage() -> str:
    e = etalonnage()
    rows = [("Holm, 25 tests nuls", e["holm"]["holm"], e["holm"]["sans_correction"]),
            ("Sharpe dégonflé, 10 essais", e["dsr"]["dsr"], e["dsr"]["sans_correction"]),
            ("SPA, 12 réglages nuls", e["spa_nul"]["spa"], None),
            ("Politique apprise, effet partout égal", e["a_nul"]["conclut"], None)]
    f = Fig(len(rows) * 34 + 60, "Taux de fausses alertes de chaque outil sur des donnees sans aucun avantage")
    hi = max(max(a, b or 0) for _, a, b in rows) * 1.1
    ax = Axes(f, 150, 10, W - 160, len(rows) * 34, 0, hi, -0.5, len(rows) - 0.5)
    for k, (nom, a, b) in enumerate(rows):
        y = len(rows) - 1 - k
        if b is not None:
            ax.hbar(y, 0, b, 14, "m-bar-pale", tip=f"{nom}, sans correction : {_pct(b)} de fausses alertes")
        ax.hbar(y, 0, max(a, 0.002), 8, "m-bar", tip=f"{nom} : {_pct(a, 1)} de fausses alertes")
        f.text(ax.x - 8, ax.sy(y) + 4, nom, "t-ax", "end")
        f.text(ax.sx(max(a, b or 0)) + 6, ax.sy(y) + 4, _pct(a, 1), "t-val")
    ax.vline(0.05, "m-seuil")
    ax.ticks_x(_graduations(0, hi, 3), lambda t: _pct(t), "fausses alertes (seuil 5 %)")
    _legende(f, len(rows) * 34 + 54, [("m-bar", "avec l’outil"), ("m-bar-pale", "sans correction")])
    f.h = len(rows) * 34 + 64
    return f.render()


@_fig("recoupement")
def m_recoupement() -> str:
    import json
    r = json.loads((R4.__file__ and __import__("pathlib").Path(R4.__file__).parent / "donnees" / "RECOUPEMENT4.json")
                   .read_text(encoding="utf-8"))
    rows = [("BH (statsmodels)", r["bh"]["ecart_max"]), ("Holm (statsmodels)", r["holm"]["ecart_max"]),
            ("Loi normale (scipy)", r["normale"]["Phi_ecart_max"]), ("Binomial exact (scipy)", r["binomial"]["ecart_max"]),
            ("Sharpe dégonflé", r["dsr"]["ecart_max"]), ("Moindres carrés (numpy)", r["mco"]["ecart_max"]),
            ("CSCV (2ᵉ écriture)", r["cscv"]["ecart_pbo_max"]), ("SPA (arch)", r["spa"]["ecart_moyen"])]
    vals = [(nom, 16.0 if v == 0 else min(16.0, -math.log10(v))) for nom, v in rows]
    f = Fig(len(vals) * 26 + 50, "Chiffres justes de nos outils compares aux bibliotheques de reference")
    ax = Axes(f, 150, 10, W - 160, len(vals) * 26, 0, 16, -0.5, len(vals) - 0.5)
    for k, ((nom, v), (_, brut)) in enumerate(zip(vals, rows)):
        y = len(vals) - 1 - k
        ax.hbar(y, 0, v, 14, "m-bar", tip=f"{nom} : écart {('nul' if brut == 0 else f'{brut:.1e}').replace('.', ',')}")
        f.text(ax.x - 8, ax.sy(y) + 4, nom, "t-ax", "end")
    ax.ticks_x([0, 4, 8, 12, 16], lambda t: _num(t, 0), "chiffres exacts (écart de 10 puissance moins n)")
    return f.render()


@lru_cache(maxsize=1)
def rendre() -> dict[str, str]:
    return {k: f() for k, f in FIGURES.items()}
