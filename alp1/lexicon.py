"""Lexique des sigles et tables des sept couches.

Ce module produit la partie du document qui répond à une question simple et
rarement traitée : *que désigne exactement chaque sigle affiché sur un
graphique, et que prédit-il ?* Chaque entrée du lexique renvoie à la fonction
du noyau qui la calcule, de sorte qu'aucune définition n'y reste verbale.

Les tables qui suivent le lexique appliquent le même traitement à chaque
couche : sa loi nulle, ce qu'elle exigerait pour valoir quelque chose, et la
donnée qu'il faudrait pour le vérifier.
"""

from __future__ import annotations

import math

from . import dow, fib, gex, orderflow, vprofile
from .barriers import prob_touch_single_barrier
from .costs import COST_BASE, ES, norm_cdf, stop_points
from .horizon import outcome_scaled
from .report import (
    FRICTION,
    HURST,
    INDEX_LEVEL,
    SESSION_MIN,
    SIGMA_1MIN,
    STOP_PCT,
    STOP_PTS,
    Table,
    num,
)

ADV_USD = 4.0e11             # volume quotidien du complexe indiciel, ordre de grandeur
OTE_RANGE = (fib.OTE_LOW, fib.OTE_HIGH)
EXPOSURE_20 = outcome_scaled(STOP_PTS, 20 * STOP_PTS, SESSION_MIN,
                             SIGMA_1MIN, HURST).expected_time
MU_STAR = FRICTION / EXPOSURE_20


# --- Lexique -----------------------------------------------------------------

def table_lexicon() -> Table:
    """Tous les sigles employés, avec leur formule et ce qu'ils prédisent."""
    chain = gex.reference_chain()
    lv = gex.levels(chain, INDEX_LEVEL)
    prof = vprofile.reference_profile()
    va = prof.value_area()

    rows = [
        # --- options ---
        ["0DTE", "Zero days to expiry",
         "options expirant le jour même ; gamma ∝ 1/√τ",
         "concentre le gamma de la chaîne autour du spot en fin de séance"],
        ["GEX", "Gamma Exposure",
         "Σ signe·OI·100·Γ·S²·1 %",
         f"notionnel à couvrir pour 1 % de variation ; ici "
         f"{num(lv.net_gex / 1e9, 1, 'Md$')} par 1 %"],
        ["0GW", "Gamma Wall (série 0DTE)",
         "strike de concentration gamma maximale",
         f"point d'ancrage du flux de couverture ; ici {num(lv.gamma_wall, 0)}"],
        ["CR1, CR2", "Call Resistance",
         "strikes au-dessus du spot, classés par concentration",
         f"ici {num(lv.cr1 or 0, 0)} puis {num(lv.cr2 or 0, 0)} ; le rang porte sur "
         f"la taille, non sur la distance"],
        ["PS1, PS2", "Put Support",
         "strikes en dessous du spot, même classement",
         f"ici {num(lv.ps1 or 0, 0)} puis {num(lv.ps2 or 0, 0)} ; PS2 n'est pas "
         f"« le deuxième plus bas » mais le deuxième plus gros"],
        ["HVL", "High Volatility Level",
         "racine de GEX(S) = 0",
         f"sépare le régime amortisseur du régime amplificateur ; ici "
         f"{num(lv.hvl or 0, 0)}, soit "
         f"{num(100 * ((lv.hvl or INDEX_LEVEL) - INDEX_LEVEL) / INDEX_LEVEL, 2, '%')} "
         f"du spot"],
        ["Flip, zero gamma", "Synonymes de HVL",
         "même définition",
         "les valeurs publiées diffèrent selon le périmètre retenu — 0DTE seul "
         "ou toutes échéances"],
        ["λΓ", "Boucle de couverture",
         "GEX / volume quotidien × impact",
         "amplification d'un choc exogène ; commande l'exposant d'échelle"],

        # --- profil de volume ---
        ["POC", "Point of Control",
         "argmax de l'histogramme du volume par prix",
         f"mode de la densité d'occupation, donc minimum de volatilité locale ; "
         f"ici {num(prof.poc, 0)}"],
        ["VA", "Value Area",
         "plus petit intervalle autour du POC couvrant 70 % du volume",
         f"ici {num(va.low, 0)} à {num(va.high, 0)}"],
        ["VAH / VAL", "Value Area High / Low",
         "bornes de l'aire de valeur",
         "notées HVA et LVA dans certains logiciels — même objet"],
        ["HVN", "High Volume Node",
         "maximum local proéminent du profil",
         "volatilité locale basse, traversée lente"],
        ["LVN", "Low Volume Node",
         "minimum local proéminent du profil",
         "volatilité locale haute, traversée rapide — la traversée est la "
         "définition, pas la prédiction"],
        ["Profil composite", "Somme de profils de séance",
         "même grille de prix, volumes additionnés",
         "ancrage de long terme ; le profil de séance est l'ancrage court"],

        # --- VWAP et Dow ---
        ["VWAP", "Volume Weighted Average Price",
         "Σ prix·volume / Σ volume, depuis l'ouverture",
         "prix moyen d'exécution de la séance ; référence d'inventaire"],
        ["Bande k σ", "Écart-type de l'écart au VWAP",
         "σ(t) = σ₁·√t",
         f"la séance passe {num(2 * norm_cdf(-3.0) * SESSION_MIN, 1)} min "
         f"au-delà de 3 σ, contre "
         f"{num(2 * norm_cdf(-1.0) * SESSION_MIN, 0)} min au-delà de 1 σ"],
        ["HH, HL, LH, LL", "Higher High, Higher Low, Lower High, Lower Low",
         "pivots successifs comparés au précédent de même nature",
         "définition structurelle de la tendance chez Dow"],
        ["Zigzag δ", "Seuil de détection de pivot",
         "un extrême devient pivot après un renversement de δ",
         "seule définition causale d'un sommet ; δ est le paramètre libre "
         "de la couche"],

        # --- Fibonacci ---
        ["φ", "Nombre d'or",
         "(1 + √5)/2 ≈ 1,618",
         "origine arithmétique des ratios ; aucun mécanisme de marché associé"],
        ["0,618 / 0,786", "Ratios de Fibonacci",
         "1/φ et √(1/φ)",
         f"probabilité nulle d'atteinte : "
         f"{num(100 * fib.p_retrace_null(0.618), 0, '%')} et "
         f"{num(100 * fib.p_retrace_null(0.786), 0, '%')}"],
        ["0,500 / 0,705", "Niveaux tracés sans généalogie Fibonacci",
         "la moitié ; moyenne de 0,618 et 0,79",
         "0,5 vient de Dow ; 0,705 est une construction de praticien"],
        ["OTE", "Optimal Trade Entry",
         "zone 0,618–0,79 du retracement",
         "grille de placement d'ordres limites, évaluée en espérance par signal"],

        # --- carnet ---
        ["L1 / L2 / L3", "Profondeurs de diffusion du carnet",
         "meilleure limite / tailles par niveau / ordres individuels",
         "la lecture d'absorption exige L2 horodaté, et L3 pour distinguer "
         "annulation et exécution"],
        ["LPR", "Liquidity Persistence Ratio",
         "taille restante au contact / taille affichée avant",
         "sépare l'absorption réelle du leurre ; introduit par ce papier"],
        ["Absorption", "Volume agressif absorbé sans déplacement",
         "LPR élevé au contact",
         "le niveau a une chance de contenir le prix"],
        ["Spoofing", "Taille affichée sans intention d'exécution",
         "LPR effondré au contact",
         "signal inverse de l'apparence ; pratique illégale et néanmoins présente"],
        ["CVD", "Cumulative Volume Delta",
         "Σ (volume à l'ask − volume au bid)",
         f"une divergence de signe survient dans "
         f"{num(100 * orderflow.p_sign_divergence(0.80), 0, '%')} des fenêtres "
         f"sous une corrélation de 0,80, sans information"],
        ["Kyle λ", "Coefficient d'impact",
         "tick / profondeur",
         "rend la friction endogène : elle monte quand le carnet s'amincit"],

        # --- grandeurs du papier ---
        ["c / L", "Friction rapportée au risque",
         f"{num(FRICTION, 2)} pt / {num(STOP_PTS, 2)} pt",
         f"{num(100 * FRICTION / STOP_PTS, 1, '%')} ; lift relatif exigé du signal, "
         f"invariant en ratio"],
        ["µ*", "Dérive d'équilibre",
         "c / E[τ∧T]",
         f"{num(MU_STAR * 60, 3)} point par heure au ratio 1:20"],
        ["E[τ∧T]", "Exposition moyenne",
         "durée de position espérée, clôture comprise",
         f"{num(EXPOSURE_20, 1)} min au ratio 1:20 ; seul canal par lequel la "
         f"géométrie agit"],
        ["H", "Exposant d'échelle",
         "σ(T) = σ₁·T^H",
         f"{num(HURST, 3)} sous la calibration retenue ; décide de "
         f"l'atteignabilité des targets éloignés"],
    ]
    return Table(
        "lexicon",
        "Lexique des sigles employés par la pile, avec leur définition calculatoire "
        "et ce qu'ils prédisent effectivement.",
        ["Sigle", "Nom", "Définition", "Ce qu'il dit"],
        rows, wrap_cols=[1, 2, 3], wide=True,
        rules_after=[8, 14, 18, 22, 27],
        note="La quatrième colonne est la seule qui engage quelque chose. Un sigle "
             "dont elle ne contient qu'une propriété de variance ou de temps de "
             "séjour — c'est le cas de la majorité — ne peut pas produire de dérive "
             "par lui-même, et n'entre dans l'espérance que par le conditionnement "
             "qu'il permet.")


# --- Gamma -------------------------------------------------------------------

def table_gex_levels() -> Table:
    """Les niveaux d'une chaîne 0DTE, reconstruits depuis la chaîne."""
    chain = gex.reference_chain()
    spot = INDEX_LEVEL
    lv = gex.levels(chain, spot)
    conc = chain.potential_notional_by_strike()

    def row(name: str, level: float | None, reading: str) -> list[str]:
        if level is None:
            return [name, "—", "—", "—", reading]
        dist = 100.0 * (level - spot) / spot
        return [name, num(level, 0), num(dist, 2, "%"),
                num(conc.get(level, 0.0) / 1e9, 1),
                reading]

    rows = [
        row("Spot", spot, "point d'évaluation de toute la chaîne"),
        row("0GW — gamma wall", lv.gamma_wall,
            f"porte {num(100 * gex.pin_strength(chain, lv.gamma_wall, spot), 0, '%')} "
            f"du gamma total : aimant en régime positif"),
        row("CR1", lv.cr1, "flux de couverture vendeur en régime positif ; "
                           "s'épuise une fois franchi"),
        row("CR2", lv.cr2, "second par la taille, plus éloigné"),
        row("PS1", lv.ps1, "strike de protection ; le flux de couverture s'y "
                           "épuise plutôt qu'il n'y pousse"),
        row("PS2", lv.ps2, "second par la taille — plus proche du spot que PS1"),
        row("HVL", lv.hvl, "sous ce niveau, la couverture amplifie au lieu d'amortir"),
    ]
    target20 = spot + 20 * STOP_PTS
    rows.append(["Target 1:20", num(target20, 0),
                 num(100 * 20 * STOP_PTS / spot, 2, "%"), "—",
                 "situé au-delà de CR2 : le trajet traverse la zone de flux la "
                 "plus dense"])
    return Table(
        "gex_levels",
        "Niveaux reconstruits depuis une chaîne 0DTE synthétique, spot "
        f"{num(spot, 0)}, {num(195, 0)} minutes avant l'échéance.",
        ["Niveau", "Prix", "Distance", "Concentration (Md$)", "Lecture"],
        rows, wrap_last=True, wide=True, rules_after=[7],
        note="La concentration est évaluée en supposant le spot au strike — "
             "convention prospective. Évalués au spot du jour, les mêmes murs "
             "désignent les strikes voisins : deux tableaux de bord peuvent donc "
             "publier des niveaux différents pour la même chaîne sans qu'aucun "
             "ne se trompe.")


def table_gex_regime() -> Table:
    """De l'exposition gamma à l'atteignabilité du target, en une chaîne."""
    rows = []
    for gex_usd in (6.0e10, 3.0e10, 0.0, -3.0e10, -6.0e10, -1.2e11):
        k = gex.gamma_feedback_coefficient(gex_usd, ADV_USD)
        h = gex.hurst_from_feedback(k, SESSION_MIN)
        rho = gex.autocorrelation_from_feedback(k)
        o20 = outcome_scaled(STOP_PTS, 20 * STOP_PTS, SESSION_MIN, SIGMA_1MIN, h)
        o30 = outcome_scaled(STOP_PTS, 30 * STOP_PTS, SESSION_MIN, SIGMA_1MIN, h)
        rows.append([
            num(gex_usd / 1e9, 0, "Md$"),
            num(k, 3, signed=True),
            num(rho, 3, signed=True),
            num(gex.vol_multiplier(k), 3),
            num(h, 3),
            num(100 * o20.p_target, 2, "%"),
            num(100 * o30.p_target, 2, "%"),
            num(o20.expected_time, 1),
        ])
    req = gex.required_gex_for_hurst(HURST, ADV_USD, horizon_min=SESSION_MIN)
    k_req = gex.feedback_from_hurst(HURST, SESSION_MIN)
    o20 = outcome_scaled(STOP_PTS, 20 * STOP_PTS, SESSION_MIN, SIGMA_1MIN, HURST)
    o30 = outcome_scaled(STOP_PTS, 30 * STOP_PTS, SESSION_MIN, SIGMA_1MIN, HURST)
    rows.append([
        num(req / 1e9, 0, "Md$"), num(k_req, 3, signed=True),
        num(gex.autocorrelation_from_feedback(k_req), 3, signed=True),
        num(gex.vol_multiplier(k_req), 3), num(HURST, 3),
        num(100 * o20.p_target, 2, "%"), num(100 * o30.p_target, 2, "%"),
        num(o20.expected_time, 1),
    ])
    return Table(
        "gex_regime",
        "Chaîne complète du gamma à l'atteignabilité : boucle de couverture, "
        "autocorrélation induite, exposant d'échelle et probabilité de target.",
        ["GEX net", "λΓ", "ρ", "σ_eff / σ", "H", "P(1:20)", "P(1:30)", "E[τ] (min)"],
        rows, rules_after=[6],
        note="La dernière ligne n'est pas une observation : c'est le gamma qu'il "
             "faudrait pour produire l'exposant d'échelle retenu par la "
             "calibration du papier. Il vaut environ quarante pour cent du volume "
             "quotidien du complexe indiciel, soit un ordre de grandeur au-dessus "
             "de tout gamma observé, et se situe à un cinquième du seuil où "
             "l'autocorrélation atteint l'unité. La persistance calibrée ne peut "
             "donc pas être attribuée au régime de gamma ; elle appelle une autre "
             "explication — saisonnalité intraséance de la volatilité, ou "
             "surestimation de la dispersion de séance.")


def table_hurst_sensitivity() -> Table:
    """Sensibilité des conclusions du papier à l'exposant d'échelle."""
    rows = []
    sqrt_disp = SIGMA_1MIN * math.sqrt(SESSION_MIN)
    p30_ref = outcome_scaled(STOP_PTS, 30 * STOP_PTS, SESSION_MIN,
                             SIGMA_1MIN, HURST).p_target
    p30_alt = outcome_scaled(STOP_PTS, 30 * STOP_PTS, SESSION_MIN,
                             SIGMA_1MIN, 0.570).p_target
    for h, label in ((0.500, "dispersion en racine du temps"),
                     (0.570, "les 60 points lus comme amplitude haut-bas"),
                     (0.600, "hypothèse intermédiaire"),
                     (HURST, "calibration retenue : 60 points d'écart-type"),
                     (0.700, "persistance plus forte encore")):
        o20 = outcome_scaled(STOP_PTS, 20 * STOP_PTS, SESSION_MIN, SIGMA_1MIN, h)
        o30 = outcome_scaled(STOP_PTS, 30 * STOP_PTS, SESSION_MIN, SIGMA_1MIN, h)
        disp = sqrt_disp * SESSION_MIN ** (h - 0.5)
        rows.append([
            num(h, 3), num(disp, 0), num(100 * disp / INDEX_LEVEL, 2, "%"),
            num(100 * o20.p_target, 2, "%"), num(100 * o30.p_target, 2, "%"),
            num(o20.expected_time, 1),
            num(FRICTION / o20.expected_time * 60, 3),
            label,
        ])
    return Table(
        "hurst_sensitivity",
        "Ce que devient la conclusion du papier quand l'exposant d'échelle varie. "
        "Toutes les autres hypothèses sont inchangées.",
        ["H", "Dispersion (pt)", "en %", "P(1:20)", "P(1:30)", "E[τ] (min)",
         "µ* (pt/h)", "Correspond à"],
        rows, wrap_last=True, wide=True,
        note=f"C'est le paramètre le plus fragile du document, et il faut le dire. "
             f"Les 60 points de dispersion de séance sont-ils un écart-type de "
             f"clôture ou une amplitude haut-bas ? L'amplitude moyenne d'un "
             f"brownien vaut environ 1,6 écart-type ; sous la seconde lecture, "
             f"l'exposant tombe à 0,57 et la probabilité d'atteindre 1:30 passe "
             f"de {num(100 * p30_ref, 2, '%')} à {num(100 * p30_alt, 2, '%')}, "
             f"soit une division par {num(p30_ref / p30_alt, 1)}. Le premier test "
             f"du protocole porte pour cette raison sur la loi d'échelle, avant "
             f"tout signal d'entrée.")


# --- Profil de volume --------------------------------------------------------

def table_profile_levels() -> Table:
    """Chaque nœud du profil, et le risque que le même stop y représente."""
    prof = vprofile.reference_profile()
    va = prof.value_area()
    sigma_ref = SIGMA_1MIN
    entries: list[tuple[str, float]] = [("POC", prof.poc)]
    entries += [(f"VAH", va.high), ("VAL", va.low)]
    entries += [("HVN", lvl) for lvl in prof.hvn()]
    entries += [("LVN", lvl) for lvl in prof.lvn()]

    rows = []
    for name, lvl in entries:
        idx = min(range(len(prof.prices)), key=lambda i: abs(prof.prices[i] - lvl))
        vol = prof.volumes[idx]
        sig = prof.sigma_at(lvl, sigma_ref)
        rows.append([
            name, num(lvl, 0), num(vol, 0),
            num(sig, 3),
            num(prof.effective_stop_sigma(lvl, STOP_PTS, sigma_ref), 2),
            num(100 * prob_touch_single_barrier(STOP_PTS, sig, 30.0), 1, "%"),
        ])
    return Table(
        "profile_levels",
        "Nœuds du profil de séance de référence, et risque effectif d'un stop "
        f"nominal de {num(STOP_PTS, 2)} points selon le nœud d'entrée.",
        ["Nœud", "Prix", "Volume", "σ locale", "Stop (σ)", "P(stop en 30 min)"],
        rows, rules_after=[3],
        note="Le stop est le même partout, en points comme en pourcentage de "
             "l'indice. Il ne l'est pas en unités de risque : d'un LVN au POC, la "
             "probabilité d'être sorti par le bruit seul en une demi-heure varie "
             "de treize points de pourcentage. Une entrée sur LVN, telle que la "
             "pile la recommande, est donc systématiquement plus fragile que le "
             "paramétrage affiché ne le laisse croire — et la correction est "
             "immédiate : indexer la largeur du stop sur la volatilité locale du "
             "nœud plutôt que sur le niveau de l'indice.")


# --- Dow ---------------------------------------------------------------------

def table_dow_null() -> Table:
    """Fréquence des motifs de Dow sous marche aléatoire, en forme fermée."""
    up, down, inside = dow.p_close_beyond_body()
    delta = 4.0
    rows = [
        ["Mèche haute ≥ corps", "1/(2k + 1), k = 1",
         num(100 * dow.p_dominant_wick(1.0), 1, "%"),
         "un jour sur trois ; la règle ne sélectionne presque rien"],
        ["Mèche haute ≥ 2 × corps", "k = 2",
         num(100 * dow.p_dominant_wick(2.0), 1, "%"),
         "sélectivité obtenue en durcissant le seuil, non en ajoutant une couche"],
        ["Mèche ≥ 4,5 × corps", "k = 4,5",
         num(100 * dow.p_dominant_wick(4.5), 1, "%"),
         "seuil correspondant à un jour sur dix"],
        ["Clôture au-dessus du corps", "3/8",
         num(100 * up, 1, "%"), "signal de continuation haussière"],
        ["Clôture sous le corps", "3/8",
         num(100 * down, 1, "%"), "signal de continuation baissière"],
        ["Clôture dans le corps", "1/4",
         num(100 * inside, 1, "%"), "absence de signal"],
        ["Nouveau sommet, repli = δ", "δ/(d + δ)",
         num(100 * dow.p_higher_high_null(delta, delta), 1, "%"),
         "la profondeur du repli fixe la fréquence, à elle seule"],
        ["Nouveau sommet, repli = 2 δ", "d = 2 δ",
         num(100 * dow.p_higher_high_null(2 * delta, delta), 1, "%"),
         "une tendance « qui respire peu » paraît fiable sans qu'aucune "
         "information ne soit en jeu"],
        ["Direction du lendemain", "½",
         num(100 * dow.p_continuation_conditional_null(), 1, "%"),
         "tout écart mesuré à cette valeur est le contenu réel de la couche"],
    ]
    return Table(
        "dow_null",
        "Fréquence exacte des motifs de Dow sous un prix sans dérive. Aucune de "
        "ces valeurs n'est estimée : ce sont des identités.",
        ["Motif", "Forme fermée", "Fréquence nulle", "Lecture"],
        rows, wrap_cols=[0, 3], wide=True, rules_after=[3, 6],
        note=f"Traduites dans le critère maître, ces fréquences deviennent une "
             f"exigence en points d'indice. Pour qu'une exposition intraséance de "
             f"{num(EXPOSURE_20, 1)} minutes couvre la friction, il faut un biais "
             f"directionnel journalier d'au moins "
             f"{num(dow.required_daily_bias(FRICTION, EXPOSURE_20, SESSION_MIN), 2)} "
             f"points, soit "
             f"{num(100 * dow.required_daily_bias(FRICTION, EXPOSURE_20, SESSION_MIN) / INDEX_LEVEL, 3)} % "
             f"de l'indice réparti uniformément sur la séance. C'est la forme sous "
             f"laquelle la couche D1 doit être testée.")


# --- Fibonacci ---------------------------------------------------------------

def table_fib_levels() -> Table:
    """Chaque niveau de la grille, sa provenance et sa loi nulle."""
    leg = fib.Leg(5960.0, 6000.0)
    rows = []
    for ratio, source in fib.RATIOS:
        p_null = fib.p_retrace_null(ratio)
        rows.append([
            num(ratio, 3), source, num(leg.level(ratio), 1),
            num(100 * p_null, 1, "%"),
            num((20 * STOP_PTS + ratio * leg.length) / STOP_PTS, 1),
            "oui" if OTE_RANGE[0] <= ratio <= OTE_RANGE[1] else "—",
        ])
    return Table(
        "fib_levels",
        "Grille de retracement sur une impulsion de "
        f"{num(leg.length, 0)} points, et probabilité qu'un prix sans dérive "
        "atteigne chaque niveau avant de prolonger de 10 %.",
        ["Ratio", "Provenance", "Niveau", "P(atteinte) nulle", "R obtenu", "Zone OTE"],
        rows, wrap_cols=[1],
        note="La colonne « R obtenu » suppose un target fixé en niveau de prix : "
             "entrer plus bas éloigne le target de l'entrée et gonfle le ratio "
             "affiché. Ce gonflement n'a aucun effet sur l'espérance — c'est le "
             "théorème d'invariance — et l'arbitrage réel se joue entre la "
             "friction épargnée sur les signaux non exécutés et la dérive perdue "
             "sur ceux qui partaient sans nous.")


# --- Liquidité ---------------------------------------------------------------

def table_liquidity_scales() -> Table:
    """Les échelles de liquidité, leur demi-vie et ce qu'elles peuvent financer."""
    rows = []
    for sc in orderflow.SCALES:
        captured = orderflow.captured_drift(1.0, sc.half_life_min, EXPOSURE_20)
        need = orderflow.required_instant_drift(FRICTION, sc.half_life_min,
                                                EXPOSURE_20)
        rows.append([
            sc.name,
            num(sc.half_life_min, 2) if sc.half_life_min < 1 else num(sc.half_life_min, 0),
            num(100 * captured, 1, "%"),
            num(need, 2),
            num(need / SIGMA_1MIN, 2),
            sc.observable,
        ])
    return Table(
        "liquidity_scales",
        f"Échelles de liquidité et dérive instantanée qu'il faudrait à chacune "
        f"pour financer une friction de {num(FRICTION, 2)} point sur une "
        f"exposition de {num(EXPOSURE_20, 1)} minutes.",
        ["Échelle", "Demi-vie (min)", "Dérive conservée", "µ₀ requis (pt/min)",
         "en σ(1 min)", "Ce qu'il faut pour l'observer"],
        rows, wrap_last=True, wide=True,
        note="La colonne « en σ(1 min) » est la plus parlante : une échelle qui "
             "exige plusieurs fois la volatilité d'une minute demande au signal de "
             "prédire un déplacement plus grand que celui que le marché produit. "
             "Les deux premières lignes sont donc irrecevables comme sources de "
             "dérive sur cette exposition, et parfaitement recevables comme outils "
             "d'exécution — décider de ne pas traverser le spread est une décision "
             "dont l'horizon est celui du signal.")


def table_layer_audit() -> Table:
    """Les sept couches, leur loi nulle, leur prédicat, leur falsifiabilité."""
    rows = [
        ["Théorie de Dow (D1)",
         "3/4 des jours déclenchent ; 1/3 montrent une mèche dominante",
         f"dérive impliquée > µ* = {num(MU_STAR * 60, 3)} pt/h",
         "OHLC journalier, gratuit",
         "falsifiable"],
        ["Supports et résistances",
         "tout niveau touché deux fois se qualifie a posteriori",
         "réaction moyenne aux niveaux pré-enregistrés contre niveaux tirés au sort",
         "OHLC intraséance, gratuit",
         "falsifiable si les niveaux sont fixés avant"],
        ["Profil de volume",
         "densité d'occupation : POC = mode, LVN = volatilité locale haute",
         "temps de traversée LVN/HVN, et écart de P(stop) entre nœuds",
         "volume par prix, payant",
         "falsifiable"],
        ["Bandes VWAP",
         f"{num(2 * norm_cdf(-3.0) * SESSION_MIN, 1)} min de séance au-delà de 3 σ",
         "dérive conditionnelle après contact, séparée par régime de gamma",
         "ticks intraséance, payant",
         "falsifiable"],
        ["Exposition gamma",
         "le signe du gamma contraint la variance, pas la direction",
         "H(Γ < 0) > H(Γ > 0), sans aucun signal d'entrée",
         "chaînes d'options et open interest, publiés",
         "falsifiable, et testable en premier"],
        ["Carnet d'ordres (L2)",
         f"AUC du LPR plafonnée vers "
         f"{num(orderflow.lpr_auc(200, 1.0, 4.0, 0.5), 2)} par recouvrement "
         f"des comportements",
         "dérive conditionnelle au LPR, sur une exposition égale à la demi-vie",
         "L2 horodaté et rejouable — un flux vidéo ne convient pas",
         "non falsifiable en l'état"],
        ["Fibonacci / OTE",
         f"taux de remplissage {num(100 * fib.expected_ote_fill(), 0, '%')} "
         f"à la borne 0,618",
         "Δ = espérance par signal, entrée en zone contre entrée au marché",
         "ticks intraséance, payant",
         "falsifiable"],
    ]
    return Table(
        "layer_audit",
        "Audit des sept couches : ce que chacune produit sous la loi nulle, ce "
        "qu'il faudrait mesurer, et si la mesure est possible.",
        ["Couche", "Loi nulle", "Prédicat testable", "Donnée requise", "Statut"],
        rows, wrap_cols=[0, 1, 2, 3, 4], wide=True,
        note="Une couche non falsifiable n'est pas une couche fausse : c'est une "
             "couche dont la contribution est indécidable, et qui ne peut donc pas "
             "être créditée d'une part de l'espérance. La sixième ligne est la "
             "seule dans ce cas, et la difficulté est d'infrastructure, non de "
             "principe — un enregistrement L2 horodaté la rendrait testable comme "
             "les autres.")


TABLES = [
    table_lexicon,
    table_gex_levels,
    table_gex_regime,
    table_hurst_sensitivity,
    table_profile_levels,
    table_dow_null,
    table_fib_levels,
    table_liquidity_scales,
    table_layer_audit,
]


def all_tables() -> dict[str, Table]:
    return {t.key: t for t in (fn() for fn in TABLES)}


def main() -> None:
    print("ALP-1 — lexique et tables des couches\n")
    for fn in TABLES:
        t = fn()
        print(f"\n### {t.caption}\n")
        print(t.to_text())


if __name__ == "__main__":
    main()
