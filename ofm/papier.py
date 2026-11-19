"""Construction du document « La personne, et non la phrase ».

Le document ne s'édite pas : on modifie `docs/ofm/la-personne.template.html`
puis on relance `python -m ofm.papier`. Les nombres du texte sont des balises
`{{clé}}` remplies ici à partir des modules ; les tables `{{TABLE:clé}}` et les
figures `{{FIGURE:clé|légende}}` sont numérotées dans l'ordre d'apparition. Une
balise non résolue fait échouer la construction.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

from alp1.discpaper import typographie
from alp1.figcss import FIGURE_CSS, FIGURE_CSS_TERMINAL, FIGURE_TOKENS_TERMINAL
from alp1.figterm import _num
from alp1.pieds import figure_html
from alp1.report import Table

from . import (calendrier, choisir, demander, donnees, mesurer, negocier, offrir,
               persuader, registre, revenir, stats, synthese)
from .figures import rendre

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "docs" / "ofm" / "la-personne.template.html"
OUTPUT = ROOT / "docs" / "ofm" / "la-personne.html"


def n0(v: float) -> str:
    return _num(v, 0)


def d1(v: float) -> str:
    return _num(v, 1)


def d2(v: float) -> str:
    return _num(v, 2)


def pc(v: float, nd: int = 1) -> str:
    return _num(v * 100, nd)


def sg(v: float, nd: int = 1) -> str:
    return ("+" if v >= 0 else "−") + _num(abs(v), nd)


def values() -> dict[str, str]:
    R = synthese.tous()
    q = synthese.q_valeurs()
    c = synthese.comptes()
    v: dict[str, str] = {}
    passes = [R[i].p for i in R if q[i] < synthese.SEUIL_Q]
    v["n_hyp"] = n0(c["total"])
    v["n_nominal"] = n0(c["nominal"])
    v["n_bruit"] = n0(c["attendus_bruit"])
    v["n_tient"] = n0(c["tient"])
    v["n_contraire"] = n0(c["contraire"])
    v["n_non"] = n0(c["non"])
    v["n_survivent"] = n0(c["tient"] + c["contraire"])
    v["n_perdus"] = n0(c["nominal"] - c["tient"] - c["contraire"])
    v["z_bh"] = d2(abs(stats.Phi_inv(max(passes) / 2)))
    v["p_bh"] = _num(max(passes), 4)
    obs = (len(donnees.raop()) + len(donnees.karlan()) + len(persuader.table())
           + len(donnees.bargain()) + len(donnees.speed()) + len(revenir.clients()))
    v["n_obs"] = n0(obs)

    # Demander
    v["raop_n"] = n0(len(demander.table()))
    v["raop_base"] = pc(demander.base_globale())
    v["raop_tendance"] = d1(abs(demander.modele().b("ans")) * 100)
    for i in [f"D{k:02d}" for k in range(1, 18)]:
        r = R[i]
        v[f"{i.lower()}_e"] = sg(r.effet)
        v[f"{i.lower()}_a"] = pc(r.extra["taux_avec"])
        v[f"{i.lower()}_s"] = pc(r.extra["taux_sans"])
        v[f"{i.lower()}_q"] = _num(q[i], 3)
        v[f"{i.lower()}_n"] = n0(r.extra["n_avec"])
    hb = demander.hors_bande()
    nu = demander.nuit()
    v["bande_dehors"], v["bande_total"] = n0(hb["dehors"]), n0(hb["total"])
    v["bande_attendus"] = d1(hb["attendus"])
    v["bande_jours"], v["bande_heures"] = n0(hb["jours"]), n0(hb["heures"])
    v["nuit_a"], v["nuit_b"], v["nuit_n"] = pc(nu["a"]), pc(nu["b"]), n0(nu["n"])
    v["nuit_p"] = _num(nu["p"], 4)
    # Offrir
    for i in ("O01", "O02", "O03", "O05", "O06"):
        r = R[i]
        v[f"{i.lower()}_a"] = pc(r.extra["a"], 2)
        v[f"{i.lower()}_b"] = pc(r.extra["b"], 2)
        v[f"{i.lower()}_e"] = sg(r.effet, 2)
        v[f"{i.lower()}_rel"] = n0(r.relatif * 100)
        v[f"{i.lower()}_lo"] = sg(r.ic[0], 2)
        v[f"{i.lower()}_hi"] = sg(r.ic[1], 2)
    v["o05_fois"] = d1(R["O05"].extra["a"] / R["O05"].extra["b"])
    v["o06_fois"] = d1(R["O06"].extra["a"] / R["O06"].extra["b"])
    v["o_rapport"] = d1((R["O05"].relatif) / R["O01"].relatif)
    v["karlan_n"] = n0(len(donnees.karlan()))
    v["karlan_dons"] = n0(sum(r["gave"] for r in donnees.karlan()))
    for i in ("O04", "O09"):
        r = R[i]
        v[f"{i.lower()}_e"] = sg(r.effet, 2)
        v[f"{i.lower()}_lo"] = sg(r.ic[0], 2)
        v[f"{i.lower()}_hi"] = sg(r.ic[1], 2)
    m = re.findall(r"effet du bonus ([+−-]?[\d,]+) pt dans les États Bush, ([+−-]?[\d,]+) pt",
                   R["O08"].lecture)
    v["o08_rouge"], v["o08_bleu"] = m[0]
    v["o10_part"] = pc(R["O10"].extra["part"])
    v["o10_n"] = n0(R["O10"].extra["n"])
    # Persuader
    v["p4g_n"] = n0(len(persuader.table()))
    v["p4g_base"] = pc(sum(l["y"] for l in persuader.table()) / len(persuader.table()))
    for i in [f"P{k:02d}" for k in range(1, 13)]:
        r = R[i]
        v[f"{i.lower()}_e"] = sg(r.effet)
        v[f"{i.lower()}_a"] = pc(r.extra["taux_avec"])
        v[f"{i.lower()}_s"] = pc(r.extra["taux_sans"])
        v[f"{i.lower()}_q"] = _num(q[i], 3)
    dg = persuader.diagnostic_reponse()
    v["libre_apres"], v["libre_base"] = pc(dg["libre"][0]), pc(dg["libre"][1])
    v["merci_apres"], v["merci_base"] = pc(dg["merci"][0]), pc(dg["merci"][1])
    v["libre_n"], v["merci_n"] = n0(dg["libre"][2]), n0(dg["merci"][2])
    v["libre_fois"] = d2(dg["libre"][0] / dg["libre"][1])
    v["merci_fois"] = d2(dg["merci"][0] / dg["merci"][1])
    # Négocier
    t = negocier.table()
    v["barg_n"] = n0(len(t))
    v["barg_acc"] = n0(sum(1 for l in t if l["valide"]))
    for i in ("N01", "N02", "N04", "N05", "N06", "N07"):
        r = R[i]
        v[f"{i.lower()}_e"] = sg(r.effet)
        v[f"{i.lower()}_a"] = pc(r.extra["moy_avec"])
        v[f"{i.lower()}_s"] = pc(r.extra["moy_sans"])
        v[f"{i.lower()}_q"] = _num(q[i], 3)
    v["n03_pente"] = d2(R["N03"].effet)
    v["n08_e"] = sg(R["N08"].effet)
    m = re.findall(r"([\d,]+) %", R["N08"].lecture)
    v["n08_a"], v["n08_s"] = m[0], m[1]
    # Choisir
    for i in ("S01", "S02", "S03", "S06", "S07"):
        r = R[i]
        v[f"{i.lower()}_e"] = sg(r.effet, 2)
        v[f"{i.lower()}_q"] = _num(q[i], 3)
    v["s01_cur"] = sg(R["S01"].extra["cur"] * 100, 1)
    v["s04_pente"] = _num(R["S04"].effet, 3)
    v["s04_r"] = _num(R["S04"].extra["r"], 3)
    v["s04_n"] = n0(R["S04"].n)
    m = re.findall(r"un point d'attrait : ([+−-]?[\d,]+) pt", R["S06"].lecture)
    v["s06_attr"] = m[0]
    ex = R["S05"].extra
    mc = choisir.polarisation_centre()[0]
    v["s05_bas"] = d1(ex["bas"] + mc)
    v["s05_haut"] = d1(ex["haut"] + mc)
    v["s05_pbas"] = sg((ex["b_s"] + ex["b_ms"] * ex["bas"]) * 100)
    v["s05_phaut"] = sg((ex["b_s"] + ex["b_ms"] * ex["haut"]) * 100)
    v["s05_q"] = _num(q["S05"], 3)
    v["speed_n"] = n0(len(donnees.speed()))
    v["speed_h"] = n0(len({s["i"] for s in choisir.sequences()}))
    v["speed_dec"] = n0(len(choisir.sequences()))
    # Revenir
    p = revenir.ajuster()
    v["bg_r"], v["bg_alpha"], v["bg_a"], v["bg_b"] = (_num(p[0], 3), _num(p[1], 3),
                                                       _num(p[2], 3), _num(p[3], 3))
    v["cd_n"] = n0(len(revenir.clients()))
    v["r01_bg"] = _num(R["R01"].extra["mae_bgnbd"], 3)
    v["r01_naif"] = _num(R["R01"].extra["mae_naif"], 3)
    v["r02_e"] = sg(R["R02"].effet, 3)
    v["r02_n"] = n0(R["R02"].n)
    v["r02_q"] = _num(q["R02"], 4)
    par = revenir.paradoxe()
    v["par_x1_reel"], v["par_x1_prev"] = d2(par[0][1]), d2(par[0][2])
    v["par_xm_reel"], v["par_xm_prev"] = d2(par[-1][1]), d2(par[-1][2])
    v["par_xm"] = n0(par[-1][0])
    v["par_xm_n"] = n0(par[-1][3])
    v["par_fois"] = d1(par[-1][1] / par[0][1])
    v["r03_bg"] = pc(R["R03"].extra["bgnbd"])
    v["r03_dep"] = pc(R["R03"].extra["depense"])
    v["r03_e"] = sg(R["R03"].effet)
    v["r04_r"] = _num(R["R04"].effet, 3)
    v["r04_var"] = pc(R["R04"].effet ** 2)
    v["r04_fois"] = d2(1 / (1 - R["R04"].effet ** 2))
    s = revenir.suivi()
    v["suivi_reel"], v["suivi_prev"] = n0(s[-1][1]), n0(s[-1][2])
    v["suivi_ecart"] = d1((s[-1][2] / s[-1][1] - 1) * -100)
    v["suivi_39_reel"], v["suivi_39_prev"] = n0(s[38][1]), n0(s[38][2])
    # validation sur l'échantillon publié
    g: dict = {}
    for x, tx, T in donnees.cdnow_echantillon():
        g[(x, tx, T)] = g.get((x, tx, T), 0) + 1
    f = lambda lp: -sum(n * revenir._ll_bgnbd([math.exp(u) for u in lp], *k) for k, n in g.items())
    lp, _ = stats.nelder_mead(f, [math.log(.25), math.log(4), math.log(.8), math.log(2.5)],
                              pas=.4, tol=1e-12)
    pe = [math.exp(u) for u in lp]
    v["val_r"], v["val_alpha"], v["val_a"], v["val_b"] = (_num(pe[0], 3), _num(pe[1], 3),
                                                         _num(pe[2], 3), _num(pe[3], 3))
    pb = revenir.ajuster_dons()
    v["bb_al"], v["bb_be"], v["bb_ga"], v["bb_de"] = (_num(pb[0], 3), _num(pb[1], 3),
                                                     _num(pb[2], 3), _num(pb[3], 3))
    v["bb_66"] = pc(revenir.p_vivant_dons(6, 6), 0)
    v["bb_11"] = pc(revenir.p_vivant_dons(1, 1), 0)
    v["bb_55"] = pc(revenir.p_vivant_dons(5, 5), 0)
    v["bb_33"] = pc(revenir.p_vivant_dons(3, 3), 0)
    # Calendrier
    rt = R["T01"]
    v["t01_e"] = sg(rt.effet, 2)
    v["t01_n"] = n0(rt.n)
    v["t01_ven"] = sg(rt.extra["vendredi"] * 100, 2)
    v["t01_nven"] = n0(rt.extra["n_vendredi"])
    v["t01_z"] = d1(abs(synthese.z_oriente("T01")))
    # Mesurer
    rg = mesurer.regarder()
    v["peek_1"] = pc(rg["naif"][1])
    v["peek_10"] = pc(rg["naif"][10])
    v["peek_100"] = pc(rg["naif"][100])
    v["peek_msprt"] = pc(max(rg["msprt"].values()), 2)
    v["peek_exp"] = n0(rg["experiences"])
    v["peek_n"] = n0(rg["n_bras"])
    gw = mesurer.surface_gagnant()
    v["gagnant_max"] = n0(gw[0][0] * 100)
    v["gagnant_min"] = d1(gw[-1][-1] * 100)
    v["budget_5_10"] = n0(stats.n_par_bras(0.05, 0.10))
    v["budget_5_50"] = n0(stats.n_par_bras(0.05, 0.50))
    v["budget_20_10"] = n0(stats.n_par_bras(0.20, 0.10))
    v["budget_1_10"] = n0(stats.n_par_bras(0.01, 0.10))
    v["cuped_budget"] = n0(stats.n_par_bras(0.05, 0.10) * (1 - R["R04"].effet ** 2))
    v["deff_10"] = d1(mesurer.effet_de_grappe(10, 0.10))
    pa = mesurer.paie()
    ia, ib = mesurer.AMPLITUDES.index(5.0), mesurer.AMPLITUDES.index(1.0)
    jn = mesurer.ACHATS.index(16)
    v["paie_5_16"] = pc(pa["puissance"][ia][jn], 0)
    v["paie_5_32"] = pc(pa["puissance"][ia][-1], 0)
    v["paie_1_32"] = pc(pa["puissance"][ib][-1], 0)
    v["paie_fp"] = pc(max(pa["faux_positifs"].values()), 1)
    v["paie_justesse_5_32"] = pc(pa["justesse"][ia][-1], 0)
    h = mesurer.horloge()
    ik = mesurer.CONCENTRATIONS.index(1.0)
    i20 = mesurer.MESSAGES.index(20)
    v["horl_1_20"] = d1(h["erreur"][ik][i20] * 60 / 60)
    v["horl_1_20_min"] = n0(h["erreur"][ik][i20] * 60)
    v["horl_025_160"] = d1(h["erreur"][-1][0])
    v["horl_4_5"] = n0(h["erreur"][0][-1] * 60)
    v["calib"] = n0(revenir.CALIB_SEM)
    v["silence"] = n0(revenir.SILENCE)
    v["cycle"] = n0(mesurer.CYCLE)
    v["fenetre"] = n0(mesurer.FENETRE)
    v["reg_sem"] = n0(max(mesurer.REGARDS))
    # Synthèse et classement
    v["transposition"] = "moitié"
    v["p_agence"] = pc(synthese.P_AGENCE, 0)
    v["envois_semaine"] = n0(synthese.ENVOIS_SEMAINE)
    cl = [(i, n) for i, _, n in synthese.classement() if n is not None]
    v["cl_premier"] = cl[0][0]
    v["cl_premier_sem"] = d1(cl[0][1] / synthese.ENVOIS_SEMAINE)
    v["cl_premier_n"] = n0(cl[0][1])
    v["n_classes"] = n0(len(cl))
    v["n_moins_mois"] = n0(sum(1 for _, n in cl if n / synthese.ENVOIS_SEMAINE <= 4.35))
    return v


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def _famille(cle: str, lettre: str, legende: str, note: str) -> Table:
    R, reg, q = synthese.tous(), registre.par_id(), synthese.q_valeurs()
    rows = []
    for i in R:
        if not i.startswith(lettre):
            continue
        h, r = reg[i], R[i]
        sens = {1: "+", -1: "−", 0: "?"}[h.sens]
        u = r.unite
        eff = f"{sg(r.effet, 2 if abs(r.effet) < 10 else 1)} {u}"
        qq = "< 0,001" if q[i] < 0.001 else _num(q[i], 3)
        rows.append([i, h.enonce, sens, r.lecture, eff, qq, synthese.verdict(i)])
    return Table(cle, legende, ["", "Hypothèse", "Pari", "Ce que montrent les données",
                                "Effet", "q", "Verdict"], rows, wrap_cols=[1, 3], wide=True,
                 note=note)


def tables() -> dict[str, Table]:
    out: dict[str, Table] = {}
    prov = donnees.provenance()
    jeux = [("raop", len(donnees.raop()), "demander un pourboire, une faveur"),
            ("karlan", len(donnees.karlan()), "un bonus attaché à l'achat, un prix suggéré"),
            ("p4g", len(persuader.table()), "une conversation de vente par écrit"),
            ("bargain", len(donnees.bargain()), "le fan qui marchande un contenu sur mesure"),
            ("speed", len(donnees.speed()), "le oui ou le non d'un homme, et l'ordre des offres"),
            ("cdnow", len(revenir.clients()), "le fan qui revient acheter, ou se tait")]
    rows = [[prov[k]["titre"], n0(n), prov[k]["unite"], ofm] for k, n, ofm in jeux]
    out["jeux"] = Table("jeux", "Les six marchés voisins. Chaque jeu est public, cloné à un "
                        "commit précis et réduit aux colonnes utiles (annexe B).",
                        ["Jeu", "Unités", "Unité d'observation", "Ce qu'il imite pour une agence"],
                        rows, wrap_cols=[0, 2, 3], wide=True)
    out["demander"] = _famille("demander", "D", "Demander — Random Acts of Pizza. Effet "
                               "ajusté en points de pourcentage de demandes servies.",
                               "« Pari » : le sens annoncé au registre (« ? » : question ouverte). "
                               "q : valeur de Benjamini-Hochberg sur les cinquante-neuf tests.")
    out["offrir"] = _famille("offrir", "O", "Offrir — Karlan et List. Le tirage au sort fait "
                             "la loi nulle ; effet en points de taux de don ou en dollars.",
                             "O07 et O08 sont des interactions : l'écart entre deux effets du bonus.")
    out["persuader"] = _famille("persuader", "P", "Persuader — Persuasion for Good. Effet ajusté "
                                "en points de pourcentage de persuadés qui donnent.",
                                "Les tactiques ne sont pas tirées au sort : voir la section 6 avant "
                                "de lire un signe.")
    out["negocier"] = _famille("negocier", "N", "Négocier — CraigslistBargain. Effet en points de "
                               "prix final rapporté à l'annonce (N03 : pente ; N08 : taux d'accord).",
                               "Contrôles : catégorie d'objet, lot, logarithme du prix affiché.")
    out["choisir"] = _famille("choisir", "S", "Choisir — speed dating de Columbia, décisions "
                              "d'hommes. Effets fixes par décideur, grappes par personne.",
                              "L'attrait est toujours la moyenne des notes données par les autres.")
    out["revenir"] = _famille("revenir", "R", "Revenir — CDNOW, calibration sur 39 semaines, "
                              "prédiction des 39 suivantes.",
                              "R02 est le seul verdict contraire du registre.")
    # Mesure : récapitulatif des étalonnages synthétiques.
    rg = mesurer.regarder()
    pa = mesurer.paie()
    hh = mesurer.horloge()
    gw = mesurer.surface_gagnant()
    ia = mesurer.AMPLITUDES.index(5.0)
    rows = [
        ["Regarder un test A/A cent fois", f"{pc(rg['naif'][100])} % de fausses victoires",
         f"{pc(max(rg['msprt'].values()), 2)} % avec un test toujours valide"],
        ["Garder la meilleure de 20 variantes nulles, 500 envois chacune",
         f"+{n0(gw[0][0] * 100)} % de hausse affichée", "planifier sur la moitié de l'effet, puis rejouer"],
        ["Lire la paie d'un fan qui dépense six fois plus après",
         f"{pc(pa['puissance'][ia][mesurer.ACHATS.index(8)], 0)} % détectées à 8 achats, "
         f"{pc(pa['puissance'][ia][-1], 0)} % à 32", f"faux positifs au plus {pc(max(pa['faux_positifs'].values()), 1)} %"],
        ["Lire l'heure d'un fan net (κ = 1)",
         f"{n0(hh['erreur'][2][mesurer.MESSAGES.index(20)] * 60)} min d'erreur médiane à 20 messages",
         f"{d1(hh['erreur'][2][-1])} h à 5 messages"],
        ["Mesurer la dépense avec sa covariable", f"{pc(synthese.tous()['R04'].effet ** 2)} % de variance en moins",
         f"budget divisé par {d2(1 / (1 - synthese.tous()['R04'].effet ** 2))}"],
    ]
    out["mesure"] = Table("mesure", "Cinq étalonnages sur séries synthétiques de vérité connue.",
                          ["Situation", "Ce qui se passe", "Parade"], rows, wrap_cols=[0, 1, 2])
    # La littérature, à tester chez soi.
    lit = [
        ["Le bonus présent plutôt que gros", "Karlan et List (2007) ; reproduit ici (O01–O03)",
         "même effet à 1:1, 2:1 et 3:1", "« un contenu offert pour un acheté », jamais plus"],
        ["Le petit cadeau avant la demande", "Falk (2007), ≈ 10 000 lettres",
         "+17 % de dons avec un petit cadeau, +75 % avec un grand", "un contenu offert avant la relance"],
        ["« Réservé pour vous »", "Milkman et al. (2021), 47 306 patients, 19 messages",
         "les messages qui présentent le vaccin comme déjà réservé font le mieux", "« je te l'ai mise de côté » pour un contenu réellement mis de côté"],
        ["Les délais courts", "Shu et Gneezy (2010)",
         "un bon valable trois semaines est bien plus utilisé qu'un bon de deux mois", "une offre de 72 heures plutôt que d'un mois"],
        ["La voix plutôt que l'écrit", "Kumar et Epley (2021)",
         "la voix crée plus de lien que le texte, et on le sous-estime", "messages vocaux enregistrés par la créatrice elle-même"],
        ["Les montants suggérés", "Haggag et Paci (2014), taxis de New York",
         "des suggestions de pourboire plus hautes élèvent le pourboire moyen", "la grille de pourboires, montants ronds (O10)"],
        ["La paie qui arrive", "Gelman et al. (2014) ; Olafsson et Pagel (2018)",
         "la dépense monte le jour de la paie, même chez qui a de l'épargne", "lire la cadence de chaque fan (section 10)"],
        ["Le dimanche des régions pieuses", "Edelman (2009)",
         "moins d'abonnements le dimanche là où la pratique religieuse est forte", "décaler le calendrier, pas le message"],
        ["L'image avant le prix", "Bertrand et al. (2010), ≈ 53 000 lettres",
         "une photo vaut une baisse de taux de 25 % — et l'effet était imprévisible", "tester les visuels comme on teste un prix"],
    ]
    out["litterature"] = Table("litterature", "Ce que la littérature établit ailleurs, et la forme "
                               "qu'un test prendrait dans une agence.",
                               ["Levier", "Source", "Ce qui est établi", "Version agence, à tester"],
                               lit, wrap_cols=[0, 1, 2, 3], wide=True,
                               note="Chaque ligne est une hypothèse à revérifier, pas un résultat "
                                    "transposable : la section 11 dit combien d'envois il faut.")
    faux = [
        ["La robe rouge", "Lehmann, Elliot et Calin-Jageman (2018)",
         "méta-analyse : effet petit (d = 0,26) chez les hommes, en déclin dans le temps"],
        ["Trop de choix fait fuir", "Scheibehenne, Greifeneder et Todd (2010)",
         "méta-analyse de 50 expériences : effet moyen voisin de zéro"],
        ["« Mais vous êtes libre »", "Fillon et al. (2023)",
         "52 expériences ; dans les sept à faible risque de biais, aucun effet — et ici, P04 négatif"],
        ["L'épuisement de la volonté", "Hagger et al. (2016)",
         "réplication préenregistrée dans 23 laboratoires : effet quasi nul"],
        ["Le cycle et les pourboires", "Miller, Tybur et Jordan (2007)",
         "dix-huit danseuses, un seul échantillon : trop peu pour fonder une pratique"],
        ["Le calendrier des demandes", "ce document, D15–D17",
         "ni le début de mois, ni le week-end, ni le soir"],
        ["La question, l'exemple, l'émotion", "ce document, P01, P03, P05",
         "aucun des trois gestes de manuel ne se lit dans les dons"],
        ["La niche clivante", "ce document, S05",
         "la dispersion des goûts coûte partout dans ce marché"],
    ]
    out["faux"] = Table("faux", "Ce qui ne tient pas, ou pas assez pour fonder une pratique.",
                        ["Croyance", "Source", "État"], faux, wrap_cols=[0, 1, 2])
    ecarte = [
        ["Fausse urgence, faux stock", "interdit dans l'UE : directive 2005/29/CE, annexe I, point 7",
         "« plus que deux heures » quand ce n'est pas vrai"],
        ["Interfaces trompeuses", "règlement sur les services numériques (UE) 2022/2065, art. 25",
         "renouvellement caché, désabonnement introuvable"],
        ["Viser la détresse ou l'ivresse", "abus de faiblesse : Code de la consommation, art. L. 121-8",
         "relancer le fan qui écrit qu'il va mal, ou à trois heures du matin ivre"],
        ["Se faire passer pour la créatrice", "pratique commerciale trompeuse (art. L. 121-2) ; règle de la maison",
         "chatteur qui jure être elle quand on le lui demande"],
        ["Fabriquer la preuve sociale", "règles de Reddit et des plateformes ; même directive",
         "votes achetés, faux « premier post », faux avis"],
        ["Récompense aléatoire payante", "jeux d'argent déguisés, régulés dans plusieurs pays",
         "« roue » payante à contenu tiré au hasard"],
    ]
    out["ecarte"] = Table("ecarte", "Ce qu'on écarte même quand cela marche : la ligne de droit, et "
                          "un exemple de ce qu'elle interdit.",
                          ["Levier", "Ce qui l'interdit", "Exemple"], ecarte, wrap_cols=[0, 1, 2],
                          note="Ce tableau n'est pas un avis juridique : il dit où chercher. Un "
                               "juriste du pays de la créatrice et des fans tranche.")
    cl = [(i, z, n) for i, z, n in synthese.classement()]
    reg = registre.par_id()
    rows = []
    for i, z, n in cl:
        sem = "—" if n is None else d1(n / synthese.ENVOIS_SEMAINE)
        env = "—" if n is None else n0(n)
        rows.append([i, reg[i].ofm, synthese.verdict(i), d1(abs(z)), env, sem])
    out["classement"] = Table("classement", "Les effets qui survivent, classés par ce qu'il "
                              "faudrait d'envois pour les revérifier chez soi.",
                              ["", "Ce que cela donne en agence", "Verdict", "|z|",
                               "Envois par variante", "Semaines"], rows, wrap_cols=[1], wide=True,
                              note=f"Budget calculé à une base déclarée de {pc(synthese.P_AGENCE, 0)} % "
                                   f"d'achat par message et à la moitié de l'effet relatif mesuré, "
                                   f"pour {n0(synthese.ENVOIS_SEMAINE)} envois par variante et par "
                                   f"semaine. « — » : effet qui ne s'exprime pas en taux (pente, "
                                   f"corrélation) ou contrôle positif.")
    # Annexe : registre complet.
    R, q = synthese.tous(), synthese.q_valeurs()
    rows = []
    for i, r in R.items():
        h = reg[i]
        rows.append([i, h.mesure, {1: "+", -1: "−", 0: "?"}[h.sens],
                     f"{sg(r.effet, 3)} [{sg(r.ic[0], 3)} ; {sg(r.ic[1], 3)}]",
                     _num(r.p, 4) if r.p >= 1e-4 else "< 0,0001",
                     _num(q[i], 4) if q[i] >= 1e-4 else "< 0,0001", n0(r.n), r.methode])
    out["registre"] = Table("registre", "Le registre complet : mesure déclarée, effet et intervalle "
                            "à 95 %, valeurs p et q, effectif, méthode.",
                            ["", "Mesure déclarée", "Pari", "Effet [IC 95 %]", "p", "q", "n",
                             "Méthode"], rows, wrap_cols=[1, 7], wide=True)
    rows = []
    for k, info in sorted(prov.items()):
        sha = info["sha256_extrait"]
        sha = sha if isinstance(sha, str) else sha[0]
        rows.append([k, info["depot"].replace("https://", ""), info["commit"][:12],
                     info["chemin"], sha[:16]])
    out["provenance"] = Table("provenance", "Provenance des données : dépôt, commit, fichier, "
                              "empreinte SHA-256 de l'extrait (16 premiers caractères).",
                              ["Jeu", "Dépôt", "Commit", "Fichier", "SHA-256"], rows,
                              wrap_cols=[1, 3], wide=True)
    return out


def build() -> str:
    text = TEMPLATE.read_text(encoding="utf-8")
    text = text.replace("{{TOKENS_TERMINAL}}", FIGURE_TOKENS_TERMINAL.rstrip("\n") + "\n")
    text = text.replace("{{FIGURE_CSS}}", FIGURE_CSS.strip("\n"))
    text = text.replace("{{FIGURE_CSS_TERMINAL}}", FIGURE_CSS_TERMINAL.strip("\n"))
    vals = values()
    for key in sorted(vals, key=len, reverse=True):
        text = text.replace("{{" + key + "}}", vals[key])
    # Renvois : `{{REF:clé}}` et `{{REFT:clé}}` prennent le numéro de la figure
    # ou de la table dans l'ordre d'apparition. Écrit à la main, un numéro de
    # figure se décale à la première planche insérée avant lui.
    ordre_f = re.findall(r"\{\{FIGURE:([a-z0-9_]+)\|", text)
    ordre_t = re.findall(r"\{\{TABLE:([a-z0-9_]+)\}\}", text)
    for k, cle in enumerate(ordre_f, 1):
        text = text.replace("{{REF:" + cle + "}}", str(k))
    for k, cle in enumerate(ordre_t, 1):
        text = text.replace("{{REFT:" + cle + "}}", str(k))
    tbl = tables()
    compteur = {"t": 0, "f": 0}

    def sub_table(m: re.Match) -> str:
        compteur["t"] += 1
        if m.group(1) not in tbl:
            raise KeyError(f"table inconnue : {m.group(1)}")
        return tbl[m.group(1)].to_html(compteur["t"])

    text = re.sub(r"\{\{TABLE:([a-z0-9_]+)\}\}", sub_table, text)
    figs = rendre()

    def sub_figure(m: re.Match) -> str:
        compteur["f"] += 1
        if m.group(1) not in figs:
            raise KeyError(f"figure inconnue : {m.group(1)}")
        return figure_html(figs[m.group(1)], compteur["f"], m.group(2).strip())

    text = re.sub(r"\{\{FIGURE:([a-z0-9_]+)\|(.+?)\}\}", sub_figure, text, flags=re.S)
    reste = re.findall(r"\{\{[^}]+\}\}", text)
    if reste:
        raise KeyError(f"balises non résolues : {sorted(set(reste))}")
    return typographie(text)


def main() -> None:
    OUTPUT.write_text(build(), encoding="utf-8")
    print(f"écrit : {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size:,} octets)")


if __name__ == "__main__":
    main()
