"""Tables chiffrées du paper ALP-1.

Chaque table est décrite une seule fois, sous forme de données, puis rendue
soit en texte (console), soit en HTML (document). Les chiffres du texte, des
tables et des figures proviennent donc tous des mêmes fonctions du noyau : ils
ne peuvent pas diverger.

Usage :
    python -m alp1.report
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from .barriers import (
    prob_target_before_stop,
    prob_touch_single_barrier,
    required_drift,
)
from .costs import (
    COST_BASE,
    COST_OPTIMISTIC,
    COST_REALISTIC,
    ES,
    breakeven_hit_rate,
    deflated_threshold_sharpe,
    stop_points,
)
from .horizon import hurst_from_dispersions, outcome, outcome_scaled
from .stops import (
    TradeGeometry,
    be_expectancy_cost_r,
    expectancy_r as managed_expectancy_r,
    outcome_probabilities,
    required_conditional_lift,
    sd_r,
    sharpe_per_trade,
)

# --- Hypothèses de marché --------------------------------------------------

INDEX_LEVEL = 6000.0
SIGMA_1MIN = 1.25            # points par racine de minute
SESSION_DISPERSION = 60.0    # points sur une séance complète, soit 1,00 % de l'indice
SESSION_MIN = 390.0
HURST = hurst_from_dispersions(SIGMA_1MIN, SESSION_DISPERSION, SESSION_MIN)

#: Largeur de stop de l'opérateur, en pourcentage du niveau d'indice.
#: **Posée par l'opérateur, encadrée.** La boîte est celle qu'il déclare :
#: cinq à dix millièmes de pour cent, soit un à deux ticks et demi sur un
#: contrat E-mini. C'est cinq à dix fois plus serré que ce que le document
#: retenait auparavant, et la conséquence n'est pas de degré : à cette
#: largeur la friction cesse d'être un prélèvement sur le risque pour en
#: devenir la moitié, puis la totalité.
STOP_PCT = 0.010
STOP_PCT_BOX = (0.005, 0.010)
RR_GRID = (20.0, 30.0)

#: Risque résiduel après remontée du stop, en pourcentage. Un dixième du
#: stop, comme auparavant : la remontée « au point mort » ne laisse jamais
#: zéro, puisque la friction reste due dans toutes les issues.
RESIDUAL_PCT = 0.001
FRICTION = COST_BASE.friction_points(ES)
TRADES_PER_DAY = 2.0

STOP_PTS = stop_points(INDEX_LEVEL, STOP_PCT)
RESIDUAL_PTS = stop_points(INDEX_LEVEL, RESIDUAL_PCT)


# --- Rendu -----------------------------------------------------------------

def num(value: float, nd: int = 2, unit: str = "", signed: bool = False) -> str:
    """Nombre à la française : virgule décimale, espace fine, vrai signe moins."""
    if value == math.inf:
        return "\u221e"
    fmt = "{:+,.%df}" % nd if signed else "{:,.%df}" % nd
    txt = (fmt.format(value).replace(",", "\u202f").replace(".", ",")
           .replace("-", "\u2212"))
    return txt + ("\u202f" + unit if unit else "")


#: `**gras**` et `` `code` ``, les deux seules marques que les notes de table
#: emploient. Elles étaient rendues telles quelles : vingt-six notes du
#: document nº 1 et deux du nº 3 publiaient leurs astérisques et leurs
#: apostrophes inverses comme des caractères. Le défaut ne se voyait pas dans
#: le code — la chaîne y est correcte — mais sur la page, ce qui est la règle
#: du dépôt : une note se regarde.
#:
#: La marque de gras exige un caractère non blanc de chaque côté. Sans cette
#: garde, `µ = 2 µ*` suivi d'une autre étoile plus loin dans la même note
#: formait une paire, et la moitié de la phrase passait en gras.
_GRAS = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", re.S)
_CODE = re.compile(r"`([^`]+)`")


def inline(text: str) -> str:
    """Rend les deux marques d'accentuation d'une note ou d'une cellule."""
    text = _GRAS.sub(r"<strong>\1</strong>", text)
    return _CODE.sub(r'<span class="v">\1</span>', text)


@dataclass
class Table:
    """Une table du paper : en-têtes, lignes déjà formatées, lecture."""

    key: str
    caption: str
    headers: list[str]
    rows: list[list[str]]
    note: str = ""
    wrap_last: bool = False
    wrap_cols: list[int] = field(default_factory=list)
    wide: bool = False
    rules_after: list[int] = field(default_factory=list)

    def to_text(self) -> str:
        out = ["| " + " | ".join(self.headers) + " |",
               "|" + "---|" * len(self.headers)]
        out += ["| " + " | ".join(r) + " |" for r in self.rows]
        if self.note:
            out += ["", self.note]
        return "\n".join(out).replace(" ", " ")

    def wrapping(self) -> set[int]:
        """Indices des colonnes autorisées à revenir à la ligne.

        Sans cette indication, une colonne de prose force la table à déborder
        de la largeur de lecture. C'est le seul réglage de mise en page que la
        description d'une table porte.
        """
        cols = set(self.wrap_cols)
        if self.wrap_last:
            cols.add(len(self.headers) - 1)
        return cols

    def to_html(self, number: int) -> str:
        cols = self.wrapping()
        head = "".join(
            "<th" + (' class="wrap"' if i in cols else "") + f">{inline(h)}</th>"
            for i, h in enumerate(self.headers))
        body = []
        for i, r in enumerate(self.rows):
            cls = ' class="sep"' if i in self.rules_after else ""
            cells = "".join(
                "<td" + (' class="wrap"' if j in cols else "")
                + f">{inline(c)}</td>"
                for j, c in enumerate(r))
            body.append(f"<tr{cls}>{cells}</tr>")
        note = (f'\n      <p class="note"><span class="lab">Lecture.</span> '
                f'{inline(self.note)}</p>'
                if self.note else "")
        klass = ' class="wide"' if self.wide else ""
        return (
            f'    <figure{klass}>\n'
            f'      <figcaption><span class="lab">Table {number}</span> — {self.caption}</figcaption>\n'
            '      <div class="scroll">\n'
            '      <table>\n'
            f'        <thead><tr>{head}</tr></thead>\n'
            '        <tbody>\n'
            + "\n".join(f'          {b}' for b in body) + '\n'
            '        </tbody>\n'
            '      </table>\n'
            '      </div>'
            f'{note}\n'
            '    </figure>'
        )


# --- Tables ----------------------------------------------------------------

def table_assumptions() -> Table:
    rows = [
        ["Contrat", "ES",
         f"{num(ES.point_value, 0)} $ le point, tick de {num(ES.tick_size, 2)} pt"],
        ["Niveau d'indice", num(INDEX_LEVEL, 0), "référence de conversion des pourcentages"],
        ["Volatilité à 1 min", num(SIGMA_1MIN, 2, "pt"), "écart-type du déplacement sur une minute"],
        ["Dispersion de séance", num(SESSION_DISPERSION, 0, "pt"),
         f"{num(100 * SESSION_DISPERSION / INDEX_LEVEL, 2)} % de l'indice, sur {num(SESSION_MIN, 0)} min"],
        ["Exposant d'échelle H", num(HURST, 3), "impliqué par les deux dispersions ci-dessus"],
        ["Stop", f"{num(STOP_PCT, 3)} %",
         f"{num(STOP_PTS, 2)} pt, {num(ES.ticks(STOP_PTS), 0)} ticks, "
         f"{num(STOP_PTS * ES.point_value, 0)} $ par contrat"],
        ["Ratios visés", "1:20 à 1:30",
         f"target {num(20 * STOP_PTS, 0)} à {num(30 * STOP_PTS, 0)} pt, soit "
         f"{num(100 * 20 * STOP_PTS / INDEX_LEVEL, 2)} à "
         f"{num(100 * 30 * STOP_PTS / INDEX_LEVEL, 2)} % de l'indice"],
        ["Risque résiduel", f"{num(RESIDUAL_PCT, 3)} % ou 0 %",
         f"{num(RESIDUAL_PTS, 2)} pt après remontée du stop ; ratio affiché jusqu'à 1:300"],
        ["Friction de référence", num(FRICTION, 2, "pt"),
         f"{num(COST_BASE.friction_usd(ES), 2)} $ par aller-retour et par contrat"],
    ]
    return Table(
        "assumptions", "Hypothèses de calcul. Toutes les tables et figures du document "
        "en découlent, sans autre paramètre libre.",
        ["Grandeur", "Valeur", "Détail"], rows, wrap_last=True,
        note="L'exposant d'échelle n'est pas choisi : il est déterminé par la volatilité "
             "à une minute et par la dispersion de la séance, deux quantités mesurables. "
             "H = 0,5 correspondrait à une dispersion en racine du temps.")


def table_geometry() -> Table:
    rows = []
    for rr in (5.0, 10.0, 20.0, 30.0):
        b = rr * STOP_PTS
        o = outcome_scaled(STOP_PTS, b, SESSION_MIN, SIGMA_1MIN, HURST)
        geom = TradeGeometry(STOP_PTS, b, FRICTION)
        p0 = 1.0 / (rr + 1.0)
        mu_star = FRICTION / o.expected_time
        rows.append([
            f"1:{rr:g}", num(b, 1), num(100 * p0, 2, "%"),
            num(100 * breakeven_hit_rate(rr, geom.friction_ratio), 2, "%"),
            num(100 * required_conditional_lift(geom), 2, "pt"),
            num(100 * geom.friction_ratio, 1, "%"),
            num(o.expected_time, 1),
            num(mu_star * 60, 3),
            num(FRICTION / (SIGMA_1MIN * math.sqrt(o.expected_time)), 3),
        ])
    return Table(
        "geometry",
        f"Exigence de signal par ratio gain/risque, stop {num(STOP_PCT, 3)} %. "
        "Exposition et dérive requise sous contrainte de séance.",
        ["R:R", "Target (pt)", "p₀", "p*", "Δp", "Δp / p₀", "E[τ∧T] (min)",
         "µ* (pt/h)", "IR requis"],
        rows,
        note="p₀ est la fréquence de touche sous martingale, p* le seuil de rentabilité, "
             "Δp l'écart entre les deux. La colonne Δp/p₀ est constante et vaut c/L : "
             "l'amélioration <em>relative</em> exigée du signal ne dépend pas du ratio "
             "retenu. Seule l'exigence absolue baisse, parce que la position reste "
             "exposée plus longtemps pour une même friction.")


def table_friction() -> Table:
    rows = []
    models = [("Optimiste", COST_OPTIMISTIC), ("Référence", COST_BASE),
              ("Réaliste", COST_REALISTIC)]
    for name, m in models:
        c = m.friction_points(ES)
        geom = TradeGeometry(STOP_PTS, 20.0 * STOP_PTS, c)
        o = outcome_scaled(STOP_PTS, 20.0 * STOP_PTS, SESSION_MIN, SIGMA_1MIN, HURST)
        rows.append([
            name, num(m.friction_usd(ES), 2), num(c, 2),
            num(c / STOP_PTS, 3),
            num(100 * required_conditional_lift(geom), 2, "pt"),
            num(c / o.expected_time * 60, 3),
            num(c / (SIGMA_1MIN * math.sqrt(o.expected_time)), 3),
        ])
    return Table(
        "friction",
        "Sensibilité à l'exécution, au ratio 1:20. La friction est le seul poste "
        "qui grève l'espérance de façon certaine.",
        ["Scénario", "Friction ($)", "c (pt)", "c/L", "Δp", "µ* (pt/h)", "IR requis"],
        rows,
        note="Le scénario optimiste suppose une entrée passive — un ordre limite "
             "qui est touché — et une sortie à un demi-tick. Il ne décrit donc que "
             "les trades entrés sur repli, jamais ceux entrés au marché sur "
             "cassure. Un même signal exécuté des deux façons ne relève pas de la "
             "même ligne de cette table, et l'écart entre les deux extrêmes vaut un "
             "facteur trois et demi sur l'exigence de signal.")


def table_session_constraint() -> Table:
    rows = []
    for rr in (5.0, 10.0, 20.0, 30.0, 50.0):
        b = rr * STOP_PTS
        d = outcome(STOP_PTS, b, SESSION_MIN, SIGMA_1MIN)
        s = outcome_scaled(STOP_PTS, b, SESSION_MIN, SIGMA_1MIN, HURST)
        rows.append([
            f"1:{rr:g}",
            num(100 / (rr + 1.0), 2, "%"),
            num(100 * d.p_target, 3, "%"), num(100 * d.p_open, 1, "%"), num(d.expected_time, 1),
            num(100 * s.p_target, 3, "%"), num(100 * s.p_open, 1, "%"), num(s.expected_time, 1),
        ])
    return Table(
        "session",
        "Effet de la clôture de séance sur les issues, sous les deux lois "
        "d'échelle. Colonnes « clôt. » : part des trades encore ouverts à la "
        "clôture ; « E[τ] » : exposition moyenne en minutes.",
        ["R:R", "p₀ sans limite", "P(TP) H=0,50", "clôt.", "E[τ]",
         "P(TP) H=0,65", "clôt.", "E[τ]"],
        rows,
        note="Sous dispersion en racine du temps, un target à 1:30 est pratiquement "
             "hors de portée d'une séance. Sous la loi d'échelle calibrée sur la "
             "dispersion réellement observée, il reste atteignable dans les trois "
             "quarts des cas où il le serait sans limite de durée. C'est cette "
             "propriété du prix — et non le ratio lui-même — qui décide de la "
             "faisabilité d'un 1:20 ou d'un 1:30.")


def table_be_distribution() -> Table:
    rows = []
    b = 20.0 * STOP_PTS
    variants = [("Stop fixe", None)] + [(f"BE à +{k:g} R", k * STOP_PTS)
                                        for k in (1.0, 2.0, 4.0, 8.0)]
    for label, trig in variants:
        g = TradeGeometry(STOP_PTS, b, FRICTION, trig)
        o = outcome_probabilities(g, 0.0, SIGMA_1MIN)
        rows.append([
            label,
            num(100 * o.p_target, 2, "%"), num(100 * o.p_breakeven, 1, "%"),
            num(100 * o.p_stop, 1, "%"), num(100 * o.apparent_hit_rate, 2, "%"),
            num(managed_expectancy_r(g, 0.0, SIGMA_1MIN), 3, signed=True),
            num(sd_r(g, 0.0, SIGMA_1MIN), 2),
            num(sharpe_per_trade(g, 0.0, SIGMA_1MIN), 4, signed=True),
        ])
    return Table(
        "be_dist",
        "Distribution des issues selon le niveau de remontée du stop. "
        "Ratio 1:20, aucune dérive, déclencheur non informatif.",
        ["Gestion", "P(TP)", "P(BE)", "P(SL)", "Hit affiché", "E[R]", "σ(R)", "SR"],
        rows,
        note="Le taux de change de la règle se lit ligne à ligne : remonter le stop "
             "au premier R ramène le taux de perte pleine de 95,2 % à 50,0 %, et "
             "coûte pour cela près de la moitié des gagnants — de 4,76 % à 2,50 %. "
             "Les deux mouvements se compensent exactement, dans toutes les lignes "
             "et à toutes les décimales.")


def table_displayed_rr() -> Table:
    """Le ratio affiché après remontée du stop, à instant et target identiques."""
    b = 30.0 * STOP_PTS
    advance = STOP_PTS                     # le prix a progressé d'un R
    d = b - advance                        # distance restante jusqu'au target
    rows = []
    variants = [
        ("Stop initial", advance + STOP_PTS),
        ("Point d'entrée", advance),
        (f"{num(RESIDUAL_PCT, 3)} % sous le prix", RESIDUAL_PTS),
    ]
    for label, r in variants:
        displayed = d / r
        effective = (d - FRICTION) / (r + FRICTION)
        p = r / (r + d)
        rows.append([
            label, num(r, 2),
            f"1:{num(displayed, 0)}", f"1:{num(effective, 0)}",
            num(100 * p, 3, "%"), num(p * displayed, 3),
            num(100 * prob_touch_single_barrier(r, SIGMA_1MIN, 5.0), 1, "%"),
        ])
    return Table(
        "displayed",
        "Le ratio affiché après remontée du stop. Même trade, même instant — le "
        "prix a progressé d'un R —, même target à 1:30 depuis l'entrée ; seule la "
        "position du stop change.",
        ["Position", "Risque (pt)", "R:R affiché", "Après friction",
         "P(TP)", "P × R:R", "Bruit 5′"],
        rows,
        note="La colonne P × R:R est le gain espéré de la branche gagnante, en "
             "multiples du risque résiduel : elle vaut environ 1 dans les trois cas. "
             "L'espérance du trade, fixée à l'entrée par la proposition 2, ne bouge "
             "pas d'une ligne à l'autre. Les deux dernières colonnes chiffrent les "
             "effets de second ordre, qui ne sont pas neutres.")


def table_be_cost() -> Table:
    b = 20.0 * STOP_PTS
    geom = TradeGeometry(STOP_PTS, b, FRICTION, STOP_PTS)
    mu_eq = required_drift(STOP_PTS, b, SIGMA_1MIN, FRICTION)
    rows = []
    for k in (-1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 3.0):
        mu2 = k * mu_eq
        cost = be_expectancy_cost_r(geom, mu_eq, SIGMA_1MIN, mu2)
        e_be = managed_expectancy_r(geom, mu_eq, SIGMA_1MIN, mu2)
        verdict = ("règle payante" if cost < -1e-9
                   else ("neutre" if abs(cost) <= 1e-9 else "règle coûteuse"))
        rows.append([num(k, 1, signed=True), num(e_be + cost, 3, signed=True),
                     num(e_be, 3, signed=True), num(cost, 3, signed=True), verdict])
    return Table(
        "be_cost",
        "Coût en R de la remontée du stop selon la dérive postérieure à la "
        "confirmation, en multiples de la dérive d'équilibre. Ratio 1:20, stop "
        "remonté au premier R.",
        ["µ₂ / µ*", "E[R] stop fixe", "E[R] avec BE", "Coût", "Verdict"],
        rows,
        note="La dérive d'entrée est maintenue à sa valeur d'équilibre ; seule la "
             "dérive postérieure à la confirmation varie, de sorte que l'écart mesure "
             "la règle et non le contenu informatif du déclencheur. Le seuil de "
             "neutralité est exactement µ₂ = 0, et le coût croît sans borne avec la "
             "qualité de la confirmation.")


def table_validation() -> Table:
    rows = []
    o20 = outcome_scaled(STOP_PTS, 20.0 * STOP_PTS, SESSION_MIN, SIGMA_1MIN, HURST)
    mu_ref = FRICTION / o20.expected_time
    for k in (1.5, 2.0, 3.0, 4.0):
        mu = k * mu_ref
        cells = [num(k, 1), num(mu * 60, 2)]
        for rr in (10.0, 20.0, 30.0):
            o = outcome_scaled(STOP_PTS, rr * STOP_PTS, SESSION_MIN, SIGMA_1MIN, HURST)
            e = (mu * o.expected_time - FRICTION) / STOP_PTS
            sr = e / (o.sd_gross / STOP_PTS)
            if sr <= 0:
                cells += ["—", "—"]
                continue
            n = (2.0 / sr) ** 2
            cells += [num(e, 3, signed=True), num(n, 0)]
        rows.append(cells)
    return Table(
        "validation",
        "Trades requis pour atteindre un t-statistique de 2, selon la dérive "
        "réellement captée à l'entrée et le ratio retenu.",
        ["µ / µ*", "pt/h", "E[R] 1:10", "N", "E[R] 1:20", "N", "E[R] 1:30", "N"],
        rows,
        note=f"À {num(TRADES_PER_DAY, 0)} trades par séance, mille trades représentent "
             "deux ans. Une dérive captée de deux points d'indice par heure — soit "
             "trois centièmes de pour cent — suffit à rendre la géométrie rentable ; "
             "la démontrer statistiquement demande davantage. Écart-type évalué sous "
             "martingale, ce qui est l'approximation correcte au voisinage du seuil.")


def table_deflation() -> Table:
    rows = []
    for trials in (10, 50, 200, 1000):
        rows.append([num(trials, 0)] +
                    [num(deflated_threshold_sharpe(trials, n), 3)
                     for n in (500, 1000, 2000)])
    return Table(
        "deflation",
        "Sharpe par trade attendu du meilleur essai sous l'hypothèse nulle, "
        "par nombre de configurations testées.",
        ["Configurations testées", "N = 500", "N = 1 000", "N = 2 000"],
        rows,
        note="Un edge réel mais modeste produit un Sharpe par trade de l'ordre de "
             "0,02 à 0,05 : il est indiscernable d'un artefact de sélection dès "
             "quelques dizaines de configurations explorées. Le nombre de "
             "configurations testées doit donc être fixé et consigné avant "
             "l'analyse, et non compté après coup — un budget non consigné rend "
             "cette table inutilisable, faute de connaître K.")


TABLES = [
    table_assumptions,
    table_geometry,
    table_friction,
    table_session_constraint,
    table_be_distribution,
    table_displayed_rr,
    table_be_cost,
    table_validation,
    table_deflation,
]


def all_tables() -> dict[str, Table]:
    return {t.key: t for t in (fn() for fn in TABLES)}


def main() -> None:
    print("ALP-1 — tables quantitatives")
    print(f"ES · indice {num(INDEX_LEVEL, 0)} · σ(1 min) = {num(SIGMA_1MIN, 2)} pt · "
          f"H = {num(HURST, 3)} · friction = {num(COST_BASE.friction_usd(ES), 2)} $/AR\n")
    for i, fn in enumerate(TABLES, start=1):
        t = fn()
        print(f"\n### Table {i} — {t.caption}\n")
        print(t.to_text())


if __name__ == "__main__":
    main()
