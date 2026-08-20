"""GEX — exposition gamma des teneurs de marché, ses niveaux et sa mécanique.

Ce module construit, à partir d'une chaîne d'options, les grandeurs que les
plateformes publient sous forme de sigles et que la pile ALP-1 utilise comme
repères. Il les définit ici par leur formule, non par leur apparence.

Vocabulaire
-----------
``0DTE``
    *Zero days to expiry*. Options expirant le jour même. Leur gamma est
    concentré sur une plage de strikes étroite autour du spot et croît comme
    ``1/√τ`` à l'approche de l'échéance : quelques heures avant la clôture,
    elles dominent le gamma total de la chaîne, même à open interest modeste.

``GEX`` — *Gamma Exposure*
    Montant notionnel que les teneurs de marché doivent échanger pour rester
    delta-neutres lorsque le sous-jacent varie de 1 %. Positif : ils vendent la
    hausse et achètent la baisse. Négatif : ils achètent la hausse et vendent
    la baisse.

``GW`` — *Gamma Wall*, préfixé ``0`` pour la série 0DTE
    Strike portant la plus forte concentration de gamma. C'est le point
    d'ancrage du flux de couverture, donc l'aimant du prix en gamma positif.

``CR`` — *Call Resistance*, ``CR1`` la première, ``CR2`` la deuxième
    Strikes au-dessus du spot classés par gamma décroissant. En gamma positif,
    la couverture y devient vendeuse à mesure que le prix monte : la
    progression s'y essouffle mécaniquement.

``PS`` — *Put Support*, ``PS1``, ``PS2``…
    Symétrique en dessous du spot. ``PS2`` est simplement le deuxième strike de
    la liste, non un niveau d'une autre nature.

``HVL`` — *High Volatility Level*
    Niveau de spot où le gamma net des teneurs change de signe. Au-dessus, la
    couverture amortit ; en dessous, elle amplifie. Les termes *gamma flip* et
    *zero gamma level* désignent le même objet ; le sigle HVL en nomme la
    conséquence plutôt que la cause. Les fournisseurs le calculent sur des
    périmètres différents (0DTE seul, toutes échéances, indice ou ETF) et
    publient donc des valeurs qui diffèrent : il est reconstruit ici pour que
    sa définition soit explicite.

Ce que ces niveaux prédisent, et ce qu'ils ne prédisent pas
-----------------------------------------------------------
Le signe du gamma net contraint une propriété de la *variance* et de
l'*autocorrélation* des rendements, jamais leur signe. La chaîne causale est
mécanique et se ferme en une formule : un gamma net Γ produit un flux de
couverture proportionnel au déplacement, ce flux a un impact de prix λ par
unité échangée, et la boucle multiplie le choc exogène par ``1/(1 + λΓ)``.
Cette rétroaction crée une autocorrélation de rendement ``ρ`` de signe opposé
à Γ, et donc un exposant d'échelle ``H`` — celui-là même dont dépend
l'atteignabilité d'un target éloigné dans `alp1.horizon`.

C'est le seul lien par lequel le gamma agit sur l'espérance d'ALP-1, et il est
entièrement quantitatif : Γ → ρ → H → P(target) → E[τ] → µ·E[τ] − c.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from .costs import norm_cdf

CONTRACT_MULTIPLIER = 100.0     # 1 contrat d'option indicielle = 100 unités
_SQRT_2PI = math.sqrt(2.0 * math.pi)
_MINUTES_PER_YEAR = 252.0 * 6.5 * 60.0


class Kind(str, Enum):
    CALL = "call"
    PUT = "put"


def norm_pdf(x: float) -> float:
    """Densité normale centrée réduite."""
    return math.exp(-0.5 * x * x) / _SQRT_2PI


def d1(spot: float, strike: float, iv: float, tau_years: float, rate: float = 0.0) -> float:
    """Premier argument de Black-Scholes."""
    if spot <= 0 or strike <= 0 or iv <= 0 or tau_years <= 0:
        raise ValueError("spot, strike, iv et tau_years doivent être > 0")
    vol = iv * math.sqrt(tau_years)
    return (math.log(spot / strike) + (rate + 0.5 * iv * iv) * tau_years) / vol


def bs_gamma(spot: float, strike: float, iv: float, tau_years: float,
             rate: float = 0.0) -> float:
    """Gamma Black-Scholes : dérivée seconde du prix par rapport au spot.

        Γ = φ(d₁) / (S·σ·√τ)

    Deux propriétés gouvernent tout ce module. Le gamma est maximal au strike,
    et sa hauteur croît comme ``1/√τ`` : une option 0DTE à deux heures de
    l'échéance porte environ ``√(6,5/2) ≈ 1,8`` fois le gamma de la même
    option en début de séance, et une option à un mois en porte une fraction
    négligeable. La concentration du gamma 0DTE autour du spot n'est donc pas
    une hypothèse, c'est une propriété de la formule.
    """
    return norm_pdf(d1(spot, strike, iv, tau_years, rate)) / (spot * iv * math.sqrt(tau_years))


def bs_delta(spot: float, strike: float, iv: float, tau_years: float,
             kind: Kind, rate: float = 0.0) -> float:
    """Delta Black-Scholes, pour situer le flux de couverture en niveau."""
    n = norm_cdf(d1(spot, strike, iv, tau_years, rate))
    return n if kind is Kind.CALL else n - 1.0


def years_to_expiry(minutes: float) -> float:
    """Convertit une durée en minutes de séance en fraction d'année.

    Le compte se fait en temps de marché, pas en temps calendaire : c'est
    pendant les séances que le gamma est couvert.
    """
    if minutes <= 0:
        raise ValueError("minutes doit être > 0")
    return minutes / _MINUTES_PER_YEAR


@dataclass(frozen=True)
class OptionLine:
    """Une ligne de chaîne : strike, type, volatilité implicite, open interest.

    `open_interest` est en contrats. Le signe du gamma détenu par les teneurs
    est décidé par `dealer_sign`, non par cette ligne.
    """

    strike: float
    kind: Kind
    iv: float
    open_interest: float

    def gamma(self, spot: float, tau_years: float, rate: float = 0.0) -> float:
        return bs_gamma(spot, self.strike, self.iv, tau_years, rate)


def dealer_sign(kind: Kind, calls_long: bool = True) -> float:
    """Signe du gamma détenu par les teneurs de marché, par type d'option.

    C'est la seule hypothèse non mécanique de tout le module, et elle mérite
    d'être isolée. La convention retenue par défaut — teneurs longs de gamma
    sur les calls, courts sur les puts — traduit le déséquilibre habituel de la
    demande finale : les investisseurs achètent de la protection en puts et
    vendent des calls couverts, les teneurs prennent l'autre côté.

    Cette convention est une régularité de flux, pas une identité comptable.
    Elle s'inverse sur un marché où la demande finale se porte sur les calls,
    ce qui suffit à changer le signe du GEX publié. Toute conclusion tirée d'un
    GEX doit donc être considérée comme conditionnelle à ce paramètre, et le
    protocole de falsification le teste plutôt que de le supposer.
    """
    if kind is Kind.CALL:
        return 1.0 if calls_long else -1.0
    return -1.0 if calls_long else 1.0


@dataclass(frozen=True)
class Chain:
    """Chaîne d'options d'une échéance, avec son temps restant."""

    lines: tuple[OptionLine, ...]
    minutes_to_expiry: float
    calls_long: bool = True

    @property
    def tau(self) -> float:
        return years_to_expiry(self.minutes_to_expiry)

    def strikes(self) -> list[float]:
        return sorted({line.strike for line in self.lines})

    def line_gex(self, line: OptionLine, spot: float, rate: float = 0.0) -> float:
        """Contribution d'une ligne au GEX, en dollars par 1 % de variation.

            GEX_ligne = signe · OI · multiplicateur · Γ · S² · 1 %

        Le facteur ``S²`` vient de deux conversions successives : ``Γ·S``
        transforme un gamma par point en variation de delta par point, et le
        second ``S`` convertit ce delta en notionnel.
        """
        g = line.gamma(spot, self.tau, rate)
        return (dealer_sign(line.kind, self.calls_long) * line.open_interest
                * CONTRACT_MULTIPLIER * g * spot * spot * 0.01)

    def gex(self, spot: float, rate: float = 0.0) -> float:
        """GEX net de la chaîne au spot donné, en dollars par 1 %."""
        return sum(self.line_gex(line, spot, rate) for line in self.lines)

    def gex_by_strike(self, spot: float, rate: float = 0.0) -> dict[float, float]:
        """GEX ventilé par strike, évalué au spot courant."""
        out: dict[float, float] = {}
        for line in self.lines:
            out[line.strike] = out.get(line.strike, 0.0) + self.line_gex(line, spot, rate)
        return dict(sorted(out.items()))

    def gamma_notional_by_strike(self, spot: float, rate: float = 0.0) -> dict[float, float]:
        """Gamma *non signé* par strike, évalué au spot courant.

        Mesure l'intensité du flux de couverture qui s'exerce **maintenant**.
        Elle est dominée par la proximité au spot : le gamma d'une option 0DTE
        décroît sur une largeur ``S·σ√τ`` — une trentaine de points à trois
        heures de l'échéance sur ES — donc tout strike distant de plus de deux
        fois cette largeur ne contribue plus, quel que soit son open interest.
        """
        out: dict[float, float] = {}
        for line in self.lines:
            g = line.gamma(spot, self.tau, rate)
            val = line.open_interest * CONTRACT_MULTIPLIER * g * spot * spot * 0.01
            out[line.strike] = out.get(line.strike, 0.0) + val
        return dict(sorted(out.items()))

    def potential_notional_by_strike(self, rate: float = 0.0) -> dict[float, float]:
        """Gamma *non signé* qu'un strike porterait si le spot l'atteignait.

        Chaque strike est évalué à la monnaie, c'est-à-dire au maximum de son
        propre gamma. On obtient une grandeur qui ne dépend plus de la position
        actuelle du prix mais seulement de l'open interest et de la volatilité
        implicite du strike.

        La distinction avec `gamma_notional_by_strike` n'est pas un détail de
        calcul : c'est la raison pour laquelle deux tableaux de bord affichent
        des murs différents pour la même chaîne. Évalué au spot, le classement
        désigne les strikes voisins — il répond à « où la couverture s'exerce
        en ce moment ». Évalué à la monnaie, il désigne les grands strikes
        ronds — il répond à « où la couverture deviendra intense si le prix y
        va ». Un niveau utilisé comme cible appartient à la seconde question,
        et c'est donc cette convention que retient `levels` par défaut.
        """
        out: dict[float, float] = {}
        for line in self.lines:
            g = bs_gamma(line.strike, line.strike, line.iv, self.tau, rate)
            val = (line.open_interest * CONTRACT_MULTIPLIER * g
                   * line.strike * line.strike * 0.01)
            out[line.strike] = out.get(line.strike, 0.0) + val
        return dict(sorted(out.items()))

    def profile(self, lo: float, hi: float, n: int = 121,
                rate: float = 0.0) -> list[tuple[float, float]]:
        """Profil ``spot → GEX(spot)`` sur une plage.

        Le GEX n'est pas une constante attachée à la chaîne : c'est une
        fonction du spot, parce que chaque gamma est réévalué au nouveau
        niveau. Confondre les deux est l'erreur de lecture la plus fréquente —
        un GEX « positif aujourd'hui » ne le reste pas 1 % plus bas.
        """
        if n < 3 or hi <= lo:
            raise ValueError("plage invalide")
        step = (hi - lo) / (n - 1)
        return [(lo + i * step, self.gex(lo + i * step, rate)) for i in range(n)]


# --- Niveaux -----------------------------------------------------------------


@dataclass(frozen=True)
class GexLevels:
    """Les niveaux publiés, reconstruits depuis la chaîne.

    Attributes
    ----------
    hvl:
        Niveau de changement de signe du gamma net (*gamma flip*, *zero gamma*).
        ``None`` si le gamma ne change pas de signe sur la plage explorée.
    gamma_wall:
        Strike de concentration gamma maximale, tous types confondus.
    call_resistance / put_support:
        Strikes au-dessus / en dessous du spot, classés par concentration
        décroissante. Le premier élément est CR1 / PS1, le deuxième CR2 / PS2.
    net_gex:
        GEX net au spot courant, en dollars par 1 %.
    """

    spot: float
    net_gex: float
    hvl: float | None
    gamma_wall: float
    call_resistance: tuple[float, ...]
    put_support: tuple[float, ...]

    @property
    def cr1(self) -> float | None:
        return self.call_resistance[0] if self.call_resistance else None

    @property
    def cr2(self) -> float | None:
        return self.call_resistance[1] if len(self.call_resistance) > 1 else None

    @property
    def ps1(self) -> float | None:
        return self.put_support[0] if self.put_support else None

    @property
    def ps2(self) -> float | None:
        return self.put_support[1] if len(self.put_support) > 1 else None

    def distance_pct(self, level: float | None) -> float | None:
        """Distance d'un niveau au spot, en pourcentage du spot."""
        if level is None or self.spot <= 0:
            return None
        return 100.0 * (level - self.spot) / self.spot


def zero_gamma_level(chain: Chain, lo: float, hi: float, rate: float = 0.0,
                     tol: float = 1e-4, max_iter: int = 200) -> float | None:
    """Niveau où le GEX net s'annule (HVL), par bissection sur le profil.

    La bissection est menée sur la *dernière* alternance de signe rencontrée en
    montant depuis `lo` : le profil peut en compter plusieurs, et le niveau
    pertinent est celui qui sépare le régime courant du régime voisin.
    """
    pts = chain.profile(lo, hi, n=241, rate=rate)
    crossings = [(pts[i][0], pts[i + 1][0])
                 for i in range(len(pts) - 1)
                 if pts[i][1] == 0.0 or pts[i][1] * pts[i + 1][1] < 0.0]
    if not crossings:
        return None
    a, b = crossings[-1]
    fa = chain.gex(a, rate)
    for _ in range(max_iter):
        mid = 0.5 * (a + b)
        fm = chain.gex(mid, rate)
        if abs(b - a) < tol or fm == 0.0:
            return mid
        if fa * fm < 0.0:
            b = mid
        else:
            a, fa = mid, fm
    return 0.5 * (a + b)


def levels(chain: Chain, spot: float, depth: int = 3, rate: float = 0.0,
           span_pct: float = 3.0, mode: str = "potential") -> GexLevels:
    """Reconstruit HVL, gamma wall, CR1…CRn et PS1…PSn depuis la chaîne.

    `mode` choisit la convention de classement des murs : ``"potential"``
    évalue chaque strike à la monnaie — c'est la lecture prospective, celle qui
    a un sens pour placer un target ; ``"spot"`` l'évalue au niveau courant —
    c'est la lecture instantanée du flux en cours. Voir
    `Chain.potential_notional_by_strike`.
    """
    if mode == "potential":
        conc = chain.potential_notional_by_strike(rate)
    elif mode == "spot":
        conc = chain.gamma_notional_by_strike(spot, rate)
    else:
        raise ValueError("mode doit valoir 'potential' ou 'spot'")
    if not conc:
        raise ValueError("chaîne vide")

    wall = max(conc.items(), key=lambda kv: kv[1])[0]
    above = sorted(((k, v) for k, v in conc.items() if k > spot),
                   key=lambda kv: -kv[1])[:depth]
    below = sorted(((k, v) for k, v in conc.items() if k < spot),
                   key=lambda kv: -kv[1])[:depth]

    lo = spot * (1.0 - span_pct / 100.0)
    hi = spot * (1.0 + span_pct / 100.0)
    return GexLevels(
        spot=spot,
        net_gex=chain.gex(spot, rate),
        hvl=zero_gamma_level(chain, lo, hi, rate),
        gamma_wall=wall,
        call_resistance=tuple(k for k, _ in above),
        put_support=tuple(k for k, _ in below),
    )


# --- Mécanique : du gamma au flux, du flux à la loi d'échelle ----------------


def hedge_flow_usd(net_gex: float, move_pct: float) -> float:
    """Notionnel que les teneurs doivent échanger pour un déplacement donné.

    Le GEX étant exprimé par 1 % de variation, le flux est proportionnel :
    un GEX de 2 milliards par 1 % impose 1 milliard de couverture pour un
    déplacement d'un demi-pourcent. Le signe indique le sens : positif, les
    teneurs vendent la hausse.
    """
    return net_gex * move_pct


def gamma_feedback_coefficient(net_gex: float, adv_usd: float,
                               impact_pct_per_adv: float = 1.0) -> float:
    """Coefficient de boucle ``λΓ``, sans dimension.

    Le flux de couverture ``Γ·dS`` a un impact de prix. En prenant pour mesure
    d'impact le déplacement, en pourcentage, provoqué par l'échange d'un volume
    égal au volume quotidien moyen (`adv_usd`), la boucle vaut

        k = λΓ = GEX / ADV · (impact par ADV).

    Un GEX de 5 milliards par 1 % sur un marché dont l'ADV vaut 250 milliards,
    avec un impact d'un pourcent par ADV échangé, donne ``k = 0,02`` : la
    couverture absorbe 2 % du choc. L'ordre de grandeur, et non la valeur, est
    ce que ce module prétend fournir.
    """
    if adv_usd <= 0:
        raise ValueError("adv_usd doit être > 0")
    return impact_pct_per_adv * net_gex / adv_usd


def vol_multiplier(feedback: float) -> float:
    """Multiplicateur de volatilité réalisée sous rétroaction de couverture.

        dS = dS₀ − λΓ·dS   =>   dS = dS₀ / (1 + λΓ)

    Gamma positif : le multiplicateur est inférieur à 1, la volatilité est
    comprimée. Gamma négatif : il excède 1, et diverge quand ``λΓ → −1`` — la
    boucle devient auto-entretenue. C'est la forme mathématique de ce qu'on
    appelle un *gamma squeeze*, et elle explique pourquoi le régime négatif est
    non seulement plus volatil mais instable.
    """
    if feedback <= -1.0:
        return math.inf
    return 1.0 / (1.0 + feedback)


def autocorrelation_from_feedback(feedback: float) -> float:
    """Autocorrélation de rendement induite par la boucle de couverture.

    Le flux de couverture d'un pas est déclenché par le rendement du pas
    précédent et s'exerce en sens contraire de Γ. À l'ordre un, le rendement
    observé suit un AR(1) de coefficient

        ρ = −λΓ / (1 + λΓ).

    Gamma positif : ρ < 0, retour à la moyenne, les extrêmes de bande tiennent.
    Gamma négatif : ρ > 0, persistance, les cassures s'étendent. C'est
    exactement la distinction entre les deux playbooks de `alp1.regime`, ici
    dérivée plutôt que postulée.

    Deux seuils, à ne pas confondre. En ``λΓ = −½`` l'autocorrélation atteint 1 :
    les rendements cessent d'être stationnaires et la dispersion croît
    linéairement en temps au lieu de croître en racine — c'est la forme
    quantitative du *gamma squeeze*. En ``λΓ = −1`` c'est l'amplification d'un
    seul pas qui diverge. Le premier seuil est le plus contraignant et c'est
    lui qui borne le domaine où cette formule a un sens.
    """
    if feedback <= -0.5:
        raise ValueError(
            "λΓ ≤ −½ : autocorrélation ≥ 1, le régime n'est plus stationnaire")
    return -feedback / (1.0 + feedback)


def dispersion_ratio(rho: float) -> float:
    """Rapport entre la dispersion d'un AR(1) agrégé et celle d'un bruit blanc.

        Var(Σ_{i≤n} r_i) ≈ n·σ²·(1 + ρ)/(1 − ρ)

    La racine de ce facteur est le rapport des écarts-types, c'est-à-dire
    exactement ce que mesure l'écart entre la volatilité à une minute et la
    dispersion d'une séance.
    """
    if not -1.0 < rho < 1.0:
        raise ValueError("rho doit être dans ]−1, 1[")
    return math.sqrt((1.0 + rho) / (1.0 - rho))


def hurst_from_feedback(feedback: float, horizon_min: float = 390.0) -> float:
    """Exposant d'échelle impliqué par la boucle de couverture.

        σ(T) = σ₁·√T·κ(ρ) = σ₁·T^H   =>   H = ½ + ln κ / ln T

    C'est le point de jonction entre ce module et `alp1.horizon` : le régime de
    gamma ne se contente pas de « comprimer la volatilité », il déplace
    l'exposant dont dépend l'atteignabilité d'un target à 1:20 ou 1:30. La
    prédiction ``H(Γ < 0) > H(Γ > 0)`` se teste sans aucun signal d'entrée.
    """
    if horizon_min <= 1:
        raise ValueError("horizon_min doit être > 1")
    rho = autocorrelation_from_feedback(feedback)
    return 0.5 + math.log(dispersion_ratio(rho)) / math.log(horizon_min)


def feedback_from_hurst(hurst: float, horizon_min: float = 390.0) -> float:
    """Boucle ``λΓ`` qu'exigerait un exposant d'échelle donné.

    Inverse de `hurst_from_feedback`. Sa raison d'être est critique : elle
    permet de demander à une calibration en `H` ce qu'elle suppose du marché.
    Si le ``λΓ`` requis dépasse les ordres de grandeur plausibles du gamma
    d'un indice, la calibration doit être expliquée autrement — par exemple par
    une saisonnalité intraséance de la volatilité — et non attribuée au gamma.
    """
    if horizon_min <= 1:
        raise ValueError("horizon_min doit être > 1")
    kappa = horizon_min ** (hurst - 0.5)
    ratio = kappa * kappa                      # (1+ρ)/(1−ρ)
    rho = (ratio - 1.0) / (ratio + 1.0)
    if rho >= 1.0:
        return -1.0
    return -rho / (1.0 + rho)


def hedge_delta(chain: Chain, spot: float, rate: float = 0.0) -> float:
    """Delta net que les teneurs doivent porter, en unités de sous-jacent.

    C'est la primitive du GEX, et c'est elle qui rend le mot « mur » précis.
    Le flux de couverture entre deux niveaux n'est pas proportionnel au gamma
    au spot mais à la *variation* de ce delta : voir `hedge_flow_between`.
    """
    total = 0.0
    for line in chain.lines:
        delta = bs_delta(spot, line.strike, line.iv, chain.tau, line.kind, rate)
        total += (dealer_sign(line.kind, chain.calls_long) * line.open_interest
                  * CONTRACT_MULTIPLIER * delta)
    return total


def hedge_flow_between(chain: Chain, spot_from: float, spot_to: float,
                       rate: float = 0.0) -> float:
    """Unités de sous-jacent à échanger pour aller d'un niveau à l'autre.

        Q = Δ(S₁) − Δ(S₀)

    Cette fonction donne la formulation défendable des notions de *mur*, de
    *support put* et de *résistance call*, et elle en corrige le récit courant.

    Le récit courant dit : « les teneurs sont courts des puts, donc ils
    achètent à ce niveau, donc il supporte ». C'est faux dans les termes mêmes
    de la convention de signe usuelle — un teneur court de gamma vend dans la
    baisse, il ne la supporte pas.

    La formulation exacte est celle-ci. Le delta d'une option sature : sous un
    strike suffisamment franchi, il ne varie plus. Le flux de couverture qu'il
    impose s'*épuise* donc, et l'épuisement est d'autant plus net que le strike
    porte d'open interest. Un mur n'est pas un niveau où un flux pousse le prix
    dans un sens : c'est un niveau où un flux cesse. Sur le graphe de Δ(S), il
    apparaît comme le point d'inflexion au-delà duquel la courbe s'aplatit.

    Cette version est mécanique, se démontre par la formule de Black-Scholes,
    et se teste : elle prédit que l'intensité du flux, et non le prix, présente
    une structure autour des grands strikes.
    """
    return hedge_delta(chain, spot_to, rate) - hedge_delta(chain, spot_from, rate)


def hurst_from_gex(net_gex: float, adv_usd: float, impact_pct_per_adv: float = 1.0,
                   horizon_min: float = 390.0) -> float:
    """Exposant d'échelle impliqué par un niveau de GEX. Composition directe."""
    return hurst_from_feedback(
        gamma_feedback_coefficient(net_gex, adv_usd, impact_pct_per_adv), horizon_min)


def required_gex_for_hurst(hurst: float, adv_usd: float,
                           impact_pct_per_adv: float = 1.0,
                           horizon_min: float = 390.0) -> float:
    """GEX net qu'exigerait un exposant d'échelle donné, en dollars par 1 %.

    Fonction de contrôle de plausibilité, et c'est son seul emploi. Elle
    répond à la question qu'une calibration en `H` ne pose jamais d'elle-même :
    quel gamma faudrait-il pour produire cette persistance ? Si la réponse
    excède d'un ordre de grandeur le gamma observable sur l'indice, la
    persistance mesurée a une autre cause, et l'attribuer au régime de gamma
    serait une erreur d'attribution.
    """
    if adv_usd <= 0 or impact_pct_per_adv <= 0:
        raise ValueError("adv_usd et impact_pct_per_adv doivent être > 0")
    k = feedback_from_hurst(hurst, horizon_min)
    return k * adv_usd / impact_pct_per_adv


def pin_strength(chain: Chain, strike: float, spot: float, rate: float = 0.0,
                 mode: str = "potential") -> float:
    """Part du gamma total portée par un strike : force d'épinglage.

    Une valeur de 0,35 signifie qu'un tiers du flux de couverture est ancré à
    ce strike. C'est la grandeur à mettre en regard d'un target : viser un
    déplacement qui traverse un mur portant l'essentiel du gamma en régime
    positif, c'est demander au prix de franchir la zone où le flux mécanique
    s'oppose le plus au mouvement.
    """
    conc = (chain.potential_notional_by_strike(rate) if mode == "potential"
            else chain.gamma_notional_by_strike(spot, rate))
    total = sum(abs(v) for v in conc.values())
    if total <= 0:
        return 0.0
    return abs(conc.get(strike, 0.0)) / total


# --- Chaîne de référence -----------------------------------------------------


def reference_chain(spot: float = 6000.0, minutes_to_expiry: float = 195.0,
                    iv: float = 0.12, step: float = 25.0, width_pct: float = 4.0,
                    calls_long: bool = True) -> Chain:
    """Chaîne 0DTE synthétique servant d'illustration dans le document.

    L'open interest reproduit trois régularités du marché indiciel, et rien de
    plus :

    1. concentration sur les strikes ronds — multiples de 100 sur ES ;
    2. open interest de calls centré légèrement au-dessus du spot, là où se
       vendent les calls couverts ;
    3. open interest de puts plus volumineux mais centré nettement en dessous,
       là où s'achète la protection — ce qui explique qu'un marché puisse être
       chargé en puts et pourtant en gamma net positif au spot : la masse de
       puts est trop éloignée pour porter du gamma ici.

    Le sourire de volatilité est ajouté parce qu'il compte : il abaisse le
    gamma des strikes bas et déplace le HVL. Aucune donnée de marché n'est
    utilisée — c'est une maquette dont la seule fonction est de rendre les
    définitions vérifiables sur un cas concret.
    """
    lo = spot * (1.0 - width_pct / 100.0)
    hi = spot * (1.0 + width_pct / 100.0)
    k = math.ceil(lo / step) * step
    lines: list[OptionLine] = []
    while k <= hi:
        m = (k - spot) / spot
        round_bonus = 1.8 if abs(k % 100.0) < 1e-9 else 1.0
        call_hump = math.exp(-((m - 0.004) / 0.011) ** 2 / 2.0)
        put_hump = math.exp(-((m + 0.022) / 0.013) ** 2 / 2.0)
        call_oi = 17_000.0 * call_hump * round_bonus
        put_oi = 18_000.0 * put_hump * round_bonus
        smile = iv * (1.0 + 1.4 * max(0.0, -m) / 0.04)
        lines.append(OptionLine(k, Kind.CALL, smile, round(call_oi)))
        lines.append(OptionLine(k, Kind.PUT, smile, round(put_oi)))
        k += step
    return Chain(tuple(lines), minutes_to_expiry, calls_long=calls_long)
