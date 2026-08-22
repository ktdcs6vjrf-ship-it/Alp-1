"""Le catalogue des dérives publiées, et ce qu'il en reste pour un retail.

Le document emprunte sa dérive à deux travaux et se demande ce que le temps
lui fait. La question symétrique n'était pas posée : **la littérature en
offre-t-elle d'autres**, et combien de pièces peut-on assembler avant que
l'assemblage coûte plus qu'il ne rapporte ?

Le module y répond avec le critère maître du document, et avec lui seul. Une
dérive publiée n'entre pas parce qu'elle est célèbre ni parce que son ratio de
Sharpe est élevé : elle entre si

    contribution = cadence · [ µ · min(exposition, horizon) − c ]

est positive **après** décote post-publication, et si son mandat, son
instrument et son coût de données sont compatibles avec la géométrie retenue.
Trois portes, et la plupart des candidats meurent à la troisième.

**Le résultat principal, et il est négatif.** Sur les neuf effets retenus —
choisis pour être documentés, intraséance ou convertibles, et exploitables sans
infrastructure institutionnelle —, un seul passe les trois portes pour un
opérateur de détail sur un contrat unique : la famille du momentum
intraséance. Or c'est celle que le document emprunte déjà. Les trois travaux
qui la composent ne sont pas trois pièces : c'est un effet publié trois fois,
et le module le facture comme tel par une décote de corrélation.

**Le second résultat porte sur l'assemblage lui-même.** Empiler `k` pièces
indépendantes de ratio d'information `i` donne `i·√k` — mais choisir lesquelles
parmi `m` candidates est une sélection sur `C(m, k)` configurations, dont le
seuil monte en `√(2 ln C(m,k)/N)`. La différence admet un maximum intérieur :
**il existe un nombre optimal de pièces, et il est petit.** Ajouter la
dixième idée à un modèle ne le dégrade pas parce qu'elle serait mauvaise, mais
parce qu'elle a été choisie.

**Le troisième porte sur la décote, et il va dans le bon sens.** Un travail
publié en 2024 sur un échantillon qui court jusqu'en 2024 est, pour un effet
publié en 2018, un test hors échantillon de l'hypothèse de décote. Le module
ne dispose pas du Sharpe scindé qui trancherait ; il publie donc le prédicat —
ce que chaque taux de décroissance impliquerait sur la seconde moitié de
l'échantillon — de sorte que le nombre, le jour où il est lu, décide sans
qu'on puisse ajuster la théorie après coup.

Statut des nombres : chaque entrée porte sa référence et son année de
publication. Les tailles d'effet sont **publiées par des tiers** et reprises
telles quelles ; leur conversion en points de base captés par minute est un
calcul de ce module, et l'hypothèse qu'elle suppose est nommée dans
`Candidate.conversion`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .decay import surviving_edge
from .entropy import kl_bernoulli

#: Niveau d'indice de référence, comme partout dans le document.
INDEX_LEVEL = 6000.0

#: Minutes d'une séance, et exposition de la géométrie ALP-2.
SESSION_MIN = 390.0
EXPOSURE_MIN = 165.6

#: Friction réaliste déduite du carnet, en points d'indice puis en pdb.
FRICTION_POINTS = 0.65
FRICTION_BPS = FRICTION_POINTS / INDEX_LEVEL * 1e4

#: Année d'évaluation du catalogue.
ASOF = 2026

@dataclass(frozen=True)
class Geometry:
    """Une géométrie du document, réduite à ce que la comparaison exige.

    `sd_r` n'est pas posé : il se **déduit** d'un couple déjà publié par le
    document — espérance de l'edge de référence et Sharpe par trade — par
    ``σ = E[R]/SR``. Les deux géométries ont leur couple, et les deux valeurs
    diffèrent d'un facteur sept parce qu'un 1:20 disperse ses issues et qu'une
    barrière unique les borne. Poser `sd_r` une seconde fois permettrait aux
    deux nombres de diverger ; le déduire l'interdit.
    """

    name: str
    reward_risk: float
    friction_ratio: float
    exposure_min: float
    edge_r: float
    sharpe_trade: float

    @property
    def sd_r(self) -> float:
        return self.edge_r / self.sharpe_trade

    def stop_bps(self, friction_bps: float = None) -> float:
        f = FRICTION_BPS if friction_bps is None else friction_bps
        return f / self.friction_ratio


#: ALP-1 : stop de trois points, ratio 1:20, exposition de 28,9 minutes.
#: Le couple publié est `E[R] = c/L = 0,110 R` et `SR/trade = 0,0332`.
GEOM_ALP1 = Geometry("ALP-1", 20.0, 0.1100, 28.9, 0.110, 0.0332)

#: ALP-2 : barrière unique sur la bande de bruit, exposition de 165,6 minutes.
#: Le couple publié est `E[R] = c/L = 0,0143 R` et le même Sharpe par trade —
#: c'est l'invariance du Sharpe sous changement de géométrie, à edge de
#: référence égal, que le document établit par ailleurs.
GEOM_ALP2 = Geometry("ALP-2", 1.0, 0.0143, 165.6, 0.0143, 0.0332)

GEOMETRIES = (GEOM_ALP1, GEOM_ALP2)

#: Convention de datation de la décote. Un effet se déprécie à partir du jour
#: où il est **publié pour la première fois**, non à chaque fois qu'il est
#: republié : l'arbitrage répond à la première parution. `"famille"` est la
#: convention retenue ; `"publication"` est conservée parce qu'elle est celle
#: que le document emploie ailleurs, et parce que l'écart entre les deux est
#: lui-même un résultat.
DATING = ("famille", "publication")
DATING_DEFAULT = "famille"


# --- Les axes de recevabilité ------------------------------------------------

#: Coût de données, du gratuit à l'inaccessible. L'échelle est ordinale et sert
#: à trancher, pas à chiffrer : ce qui compte est le seuil qu'un opérateur de
#: détail peut franchir, et il se situe entre 1 et 2.
DATA_COST = {
    0: "barres d'une minute d'un contrat, gratuites",
    1: "chaîne d'options quotidienne, abonnement modeste",
    2: "tick et carnet de niveau 2 d'un contrat, abonnement professionnel",
    3: "section transversale de milliers de titres, emprunt de titres compris",
}

#: Mandats d'exposition. Deux effets ne se combinent dans un même modèle que
#: s'ils partagent le mandat : une thèse tenue un mois ne se loge pas dans une
#: géométrie qui sort au marché à la clôture.
MANDATES = ("intraseance", "overnight", "pluriseance")

#: Mandat de la géométrie ALP-2.
MANDATE_ALP2 = "intraseance"

#: Seuil de coût de données au-delà duquel un opérateur de détail ne suit pas.
RETAIL_COST_MAX = 1


@dataclass(frozen=True)
class Candidate:
    """Une dérive publiée, réduite à ce que le critère maître lui demande.

    `effect_bps` est la taille d'effet publiée, en points de base, **par
    occurrence**. `horizon_min` est la durée sur laquelle elle s'accumule.
    `cadence` est le nombre d'occurrences par an. `conversion` nomme
    l'hypothèse qui transforme le chiffre publié en dérive par minute — c'est
    le seul endroit où ce module ajoute quelque chose au travail cité, et il
    doit donc être lisible.
    """

    key: str
    name: str
    reference: str
    year: int
    effect_bps: float
    horizon_min: float
    cadence: float
    mandate: str
    data_cost: int
    conversion: str
    family: str = ""

    def __post_init__(self) -> None:
        if self.mandate not in MANDATES:
            raise ValueError(f"mandat inconnu : {self.mandate!r}")
        if self.data_cost not in DATA_COST:
            raise ValueError(f"coût de données inconnu : {self.data_cost!r}")
        if self.horizon_min <= 0 or self.cadence <= 0:
            raise ValueError("horizon et cadence doivent être > 0")

    @property
    def drift_per_min(self) -> float:
        """Dérive publiée, ramenée au point de base par minute."""
        return self.effect_bps / self.horizon_min

    def dating_year(self, catalogue=None, dating: str = DATING_DEFAULT) -> int:
        """Année qui fait courir la décote, selon la convention retenue.

        Sous `"famille"`, c'est la première parution de l'effet, tous auteurs
        confondus : trois énoncés d'un même résultat ne remettent pas le
        compteur à zéro. Sous `"publication"`, c'est l'année de l'entrée.
        """
        if dating not in DATING:
            raise ValueError(f"convention de datation inconnue : {dating!r}")
        if dating == "publication" or not self.family:
            return self.year
        source = CATALOGUE if catalogue is None else catalogue
        return min(c.year for c in source if c.family == self.family)

    def surviving_bps(self, asof: int = ASOF, rate: float | None = None,
                      dating: str = DATING_DEFAULT) -> float:
        """Taille d'effet restante après décote post-publication."""
        an = self.dating_year(dating=dating)
        return surviving_edge(self.effect_bps, max(asof - an, 0), rate)

    def captured_bps(self, exposure_min: float = EXPOSURE_MIN,
                     asof: int = ASOF, rate: float | None = None,
                     dating: str = DATING_DEFAULT) -> float:
        """Ce qu'une position capte d'une occurrence, décote comprise.

        Une exposition plus courte que l'horizon n'en capte qu'une part ; une
        exposition plus longue n'en capte pas davantage, la dérive s'arrêtant
        avec l'effet. C'est l'identité de Wald, appliquée à un effet borné.
        """
        part = min(exposure_min, self.horizon_min) / self.horizon_min
        return self.surviving_bps(asof, rate, dating) * part

    def net_bps(self, exposure_min: float = EXPOSURE_MIN, asof: int = ASOF,
                friction_bps: float = FRICTION_BPS,
                rate: float | None = None,
                dating: str = DATING_DEFAULT) -> float:
        """Espérance nette par occurrence, en points de base."""
        return self.captured_bps(exposure_min, asof, rate, dating) - friction_bps

    def annual_bps(self, exposure_min: float = EXPOSURE_MIN, asof: int = ASOF,
                   friction_bps: float = FRICTION_BPS,
                   rate: float | None = None,
                   dating: str = DATING_DEFAULT) -> float:
        """Contribution annuelle, en points de base d'indice."""
        return self.cadence * self.net_bps(exposure_min, asof, friction_bps,
                                           rate, dating)

    def native_net_bps(self, asof: int = ASOF,
                       friction_bps: float = FRICTION_BPS,
                       dating: str = DATING_DEFAULT) -> float:
        """Espérance nette **sur le mandat propre de l'effet**.

        L'effet est alors tenu toute la durée sur laquelle il s'accumule, et
        la friction n'est payée qu'une fois. C'est la lecture juste de sa
        valeur intrinsèque ; la lecture précédente dit ce qu'il devient
        lorsqu'on tente de le loger dans une géométrie qui n'est pas la
        sienne. L'écart entre les deux est ce que la porte de mandat facture.
        """
        return self.net_bps(self.horizon_min, asof, friction_bps, None, dating)

    def native_annual_bps(self, asof: int = ASOF,
                          friction_bps: float = FRICTION_BPS,
                          dating: str = DATING_DEFAULT) -> float:
        return self.cadence * self.native_net_bps(asof, friction_bps, dating)

    def retail(self) -> bool:
        return self.data_cost <= RETAIL_COST_MAX

    def compatible(self, mandate: str = MANDATE_ALP2) -> bool:
        """Compatible avec la géométrie retenue : même mandat, coût atteignable."""
        return self.mandate == mandate and self.retail()

    def captured_for(self, geometry: Geometry, asof: int = ASOF,
                     dating: str = DATING_DEFAULT) -> float:
        """Ce que **cette** géométrie capte de l'effet, en points de base.

        C'est ici que se joue la compatibilité réelle, et elle est plus fine
        que la porte de mandat : une exposition plus longue que l'horizon de
        l'effet n'en capte pas davantage, et une exposition plus courte n'en
        capte qu'une fraction. **Les deux constantes de temps doivent se
        correspondre.** Une géométrie patiente ne tire aucun avantage d'un
        effet de trente minutes, et une géométrie brève laisse sur la table
        l'essentiel d'un effet de trois heures.
        """
        return self.captured_bps(geometry.exposure_min, asof, None, dating)

    def net_for(self, geometry: Geometry, asof: int = ASOF,
                friction_bps: float = FRICTION_BPS,
                dating: str = DATING_DEFAULT) -> float:
        return self.captured_for(geometry, asof, dating) - friction_bps

    def bits(self, geometry: Geometry = GEOM_ALP2, asof: int = ASOF,
             friction_bps: float = FRICTION_BPS,
             dating: str = DATING_DEFAULT) -> float:
        """Information **fournie** par l'effet, en bits par occurrence.

        La route est celle de `entropy.required_bits`, parcourue en sens
        inverse. Une dérive captée `µ·E[τ]` sur un risque nominal `L` déplace
        le taux de réussite de sa valeur martingale ``q = 1/(R+1)`` de

            Δp = (µ·E[τ] / L) / (R + 1),

        parce que l'espérance en multiples du risque vaut ``(R+1)·(p − q)``.
        L'information portée est la divergence de Kullback-Leibler entre les
        deux fréquences, et elle se compare à ce que la même géométrie exige.
        """
        stop = geometry.stop_bps(friction_bps)
        capte = self.captured_for(geometry, asof, dating)
        if capte <= 0.0 or stop <= 0.0:
            return 0.0
        q = 1.0 / (geometry.reward_risk + 1.0)
        p = min(q + (capte / stop) / (geometry.reward_risk + 1.0), 1.0 - 1e-12)
        return kl_bernoulli(p, q)

    def bits_ratio(self, geometry: Geometry = GEOM_ALP2, **kw) -> float:
        """Rapport de l'information fournie à l'information exigée.

        Supérieur à un, la pièce finance la géométrie ; inférieur, elle ne la
        finance pas, et aucun dimensionnement ne rattrape l'écart — c'est le
        plafond de Kelly, et il n'a pas de contournement.
        """
        from .entropy import required_bits
        exige = required_bits(geometry.reward_risk, geometry.friction_ratio).bits
        if exige <= 0.0:
            return math.inf
        return self.bits(geometry, **kw) / exige

    def information_ratio(self, geometry: Geometry = GEOM_ALP2,
                          asof: int = ASOF, friction_bps: float = FRICTION_BPS,
                          dating: str = DATING_DEFAULT) -> float:
        """Ratio d'information par occurrence, dans la géométrie donnée.

        ``IR = espérance nette / dispersion``, les deux ramenés au risque
        nominal. C'est la grandeur que l'assemblage additionne en carré, et
        c'est elle qu'il faut comparer au seuil d'entrée `1/√N`.
        """
        stop = geometry.stop_bps(friction_bps)
        if stop <= 0.0 or geometry.sd_r <= 0.0:
            return 0.0
        net_r = self.net_for(geometry, asof, friction_bps, dating) / stop
        return net_r / geometry.sd_r


# --- Le catalogue ------------------------------------------------------------

#: Neuf effets documentés. Le critère d'entrée est celui du document : un
#: travail publié, une taille d'effet chiffrée par ses auteurs, et une chance
#: sérieuse d'être exploitable sans infrastructure institutionnelle. Les
#: effets rejetés le sont par le calcul qui suit, pas par la sélection.
CATALOGUE: tuple[Candidate, ...] = (
    Candidate(
        key="mim_us",
        name="Momentum intraséance, États-Unis",
        reference="Gao, Han, Li et Zhou (2018), Journal of Financial Economics",
        year=2018,
        effect_bps=6.00,
        horizon_min=30.0,
        cadence=252.0,
        mandate="intraseance",
        data_cost=0,
        conversion="dérive de la dernière demi-heure, telle que le document "
                   "la retient déjà ; aucune conversion supplémentaire",
        family="momentum intraséance",
    ),
    Candidate(
        key="mim_intl",
        name="Momentum intraséance, généralisation internationale",
        reference="Baltussen, Da, Lammers et Martens (2021), "
                  "Journal of Financial Economics",
        year=2021,
        effect_bps=6.00,
        horizon_min=30.0,
        cadence=252.0,
        mandate="intraseance",
        data_cost=0,
        conversion="même effet, autres marchés ; la taille est reprise de la "
                   "calibration du document plutôt que recalculée",
        family="momentum intraséance",
    ),
    Candidate(
        key="bande_bruit",
        name="Franchissement de la bande de bruit",
        reference="Zarattini, Aziz et Barbon (2024), SSRN 4824172",
        year=2024,
        effect_bps=6.00,
        horizon_min=195.0,
        cadence=252.0,
        mandate="intraseance",
        data_cost=0,
        conversion="ratio de Sharpe publié converti à espérance égale à la "
                   "famille du momentum intraséance, dont l'effet relève",
        family="momentum intraséance",
    ),
    Candidate(
        key="prefomc",
        name="Dérive pré-annonce du comité de politique monétaire",
        reference="Lucca et Moench (2015), Journal of Finance",
        year=2015,
        effect_bps=49.0,
        horizon_min=1440.0,
        cadence=8.0,
        mandate="overnight",
        data_cost=0,
        conversion="rendement publié des vingt-quatre heures précédant "
                   "l'annonce, réparti uniformément sur la fenêtre",
        family="calendrier",
    ),
    Candidate(
        key="periodicite",
        name="Périodicité intraséance de la section transversale",
        reference="Heston, Korajczyk et Sadka (2010), Journal of Finance",
        year=2010,
        effect_bps=12.0,
        horizon_min=30.0,
        cadence=252.0,
        mandate="intraseance",
        data_cost=3,
        conversion="rendement d'un portefeuille long-court à demi-heure "
                   "fixe, non transposable à un contrat unique",
        family="section transversale",
    ),
    Candidate(
        key="tug_of_war",
        name="Séparation nuit / séance",
        reference="Lou, Polk et Skouras (2019), "
                  "Journal of Financial Economics",
        year=2019,
        effect_bps=35.0,
        horizon_min=390.0,
        cadence=252.0,
        mandate="pluriseance",
        data_cost=3,
        conversion="écart publié entre rendements de nuit et de séance sur un "
                   "portefeuille trié, converti par occurrence quotidienne",
        family="section transversale",
    ),
    Candidate(
        key="retail_imbalance",
        name="Déséquilibre d'ordres de détail",
        reference="Boehmer, Jones, Zhang et Zhu (2021), Journal of Finance",
        year=2021,
        effect_bps=40.0,
        horizon_min=1950.0,
        cadence=52.0,
        mandate="pluriseance",
        data_cost=3,
        conversion="rendement hebdomadaire publié d'un tri par déséquilibre, "
                   "identification des ordres de détail par le sous-cent",
        family="foule",
    ),
    Candidate(
        key="attention_retail",
        name="Herding d'attention des plateformes de détail",
        reference="Barber, Huang, Odean et Schwarz (2022), Journal of Finance",
        year=2022,
        effect_bps=100.0,
        horizon_min=8190.0,
        cadence=12.0,
        mandate="pluriseance",
        data_cost=3,
        conversion="ordre de grandeur du rendement mensuel négatif suivant les "
                   "épisodes d'attention extrême, pris à contre-pied ; "
                   "la source de popularité employée n'est plus publiée",
        family="foule",
    ),
    Candidate(
        key="antitalent",
        name="Contre-pied du talent négatif des diffuseurs",
        reference="Kakhbod, Kazempour, Livdan et Schürhoff (2023), SFI 23-30",
        year=2023,
        effect_bps=120.0,
        horizon_min=8190.0,
        cadence=12.0,
        mandate="pluriseance",
        data_cost=3,
        conversion="performance hors échantillon publiée de la stratégie de "
                   "contre-pied, 1,2 % par mois, sur une section transversale "
                   "de titres et non sur un indice",
        family="foule",
    ),
)

CATALOGUE_BY_KEY = {c.key: c for c in CATALOGUE}


def compatible(mandate: str = MANDATE_ALP2,
               cost_max: int = RETAIL_COST_MAX) -> tuple[Candidate, ...]:
    """Les candidats qui passent les portes de mandat et de coût."""
    return tuple(c for c in CATALOGUE
                 if c.mandate == mandate and c.data_cost <= cost_max)


def independent_families(cands) -> dict[str, list[Candidate]]:
    """Regroupe par famille. Une famille publiée trois fois reste une pièce."""
    out: dict[str, list[Candidate]] = {}
    for c in cands:
        out.setdefault(c.family or c.key, []).append(c)
    return out


def effective_pieces(cands, rho: float = 1.0) -> float:
    """Nombre de pièces **effectives**, corrélation intra-famille comprise.

    À l'intérieur d'une famille, `n` publications du même effet valent
    ``n / (1 + (n − 1)ρ)`` pièces : à `ρ = 1` elles n'en valent qu'une, ce qui
    est le cas par défaut et le cas honnête pour trois énoncés d'un même
    résultat. Les familles sont supposées indépendantes entre elles, ce qui
    est optimiste et joue donc contre la conclusion du module.
    """
    if not 0.0 <= rho <= 1.0:
        raise ValueError("rho doit être dans [0, 1]")
    total = 0.0
    for membres in independent_families(cands).values():
        n = len(membres)
        total += n / (1.0 + (n - 1) * rho)
    return total


# --- L'assemblage, et le seuil d'entrée d'une pièce -------------------------

def combined_ir(ir_each: float, k: float, rho: float = 0.0) -> float:
    """Ratio d'information de `k` pièces de qualité égale et corrélation `rho`.

    ``IR = i·√(k / (1 + (k − 1)ρ))``. À `ρ = 0` c'est la racine familière ; à
    `ρ = 1` l'empilement n'apporte rien, ce qui est la bonne réponse pour un
    même effet republié.
    """
    if k <= 0:
        return 0.0
    denom = 1.0 + (k - 1.0) * rho
    if denom <= 0.0:
        raise ValueError("corrélation incompatible avec k pièces")
    return ir_each * math.sqrt(k / denom)


def selection_threshold(m_candidates: int, k_kept: int, n_obs: int) -> float:
    """Seuil que la **recherche** d'un sous-ensemble impose, en IR par obs.

    Choisir `k` pièces parmi `m` en regardant les données est une famille de
    ``C(m, k)`` configurations, dont le meilleur membre sans edge affiche
    ``√(2 ln C / N)``. C'est le coût de la fouille, distinct du coût
    d'estimation ci-dessous, et il s'y ajoute.
    """
    if n_obs < 1:
        raise ValueError("n_obs doit être ≥ 1")
    if k_kept < 1 or k_kept > m_candidates:
        return math.inf
    c = math.comb(m_candidates, k_kept)
    return 0.0 if c < 2 else math.sqrt(2.0 * math.log(c) / n_obs)


def entry_threshold(n_obs: int) -> float:
    """Ratio d'information minimal d'une pièce pour mériter sa place.

    Combiner `k` signaux dont les poids sont estimés sur `N` observations
    coûte, en ratio d'information au carré, environ ``k/N`` — une unité par
    paramètre estimé, comme partout où l'on ajuste. Le carré de l'IR combiné
    hors échantillon vaut donc ``Σ i² − k/N``, et **une pièce n'améliore
    l'ensemble que si son propre IR dépasse `1/√N`.**

    Le critère est frappant par ce qu'il ne contient pas : ni le nombre de
    pièces déjà retenues, ni leur qualité, ni leur corrélation. Chaque pièce
    est jugée seule, contre un seuil que seule la taille d'échantillon fixe.
    """
    if n_obs < 1:
        raise ValueError("n_obs doit être ≥ 1")
    return 1.0 / math.sqrt(n_obs)


@dataclass(frozen=True)
class Assembly:
    """Le bilan d'un assemblage de `k` pièces : brut, coûts, net."""

    k: int
    ir_gross: float
    estimation_cost: float
    search_cost: float

    @property
    def ir_net(self) -> float:
        """IR hors échantillon : ``√(max(IR² − k/N, 0))`` moins la fouille."""
        reste = self.ir_gross ** 2 - self.estimation_cost
        return (math.sqrt(reste) if reste > 0.0 else 0.0) - self.search_cost


def assembly_scan(irs: list[float], n_obs: int,
                  rho: float = 0.0) -> list[Assembly]:
    """Bilan pour chaque nombre de pièces retenues, les meilleures d'abord.

    Les pièces sont triées par IR décroissant : c'est l'ordre dans lequel un
    assembleur rationnel les ajoute, et le seul pour lequel l'optimum a un
    sens. La corrélation `rho` s'applique entre pièces retenues.

    Une pièce d'IR négatif est **écartée**, non retournée : la retourner est
    une décision de signe, et une décision de signe prise au vu des données
    est une configuration de plus. Un effet dont la lecture est contraire
    entre au catalogue sous sa forme contraire, déclarée d'avance — c'est
    exactement le statut de l'entrée « contre-pied du talent négatif ».
    """
    if n_obs < 1:
        raise ValueError("n_obs doit être ≥ 1")
    tries = sorted((i for i in irs if i > 0.0), reverse=True)
    out = []
    for k in range(1, len(tries) + 1):
        somme = sum(i * i for i in tries[:k])
        brut = math.sqrt(somme / (1.0 + (k - 1) * rho)) if k else 0.0
        out.append(Assembly(k=k, ir_gross=brut,
                            estimation_cost=k / n_obs,
                            search_cost=selection_threshold(len(tries), k, n_obs)))
    return out


def optimal_pieces(irs: list[float], n_obs: int, rho: float = 0.0) -> Assembly:
    """Le nombre de pièces qui maximise le ratio d'information hors échantillon.

    Le maximum est intérieur dès que les pièces sont de qualité inégale : le
    gain de la `k`-ième croît comme son propre IR au carré, le coût comme
    `1/N`, constant. La conséquence pratique est la seule qui compte —
    **un modèle assemblé à partir d'un catalogue a un nombre optimal de
    pièces, il est petit, et il ne dépend pas de la qualité du catalogue mais
    de la longueur de l'échantillon qui le juge.**
    """
    scan = assembly_scan(irs, n_obs, rho)
    if not scan:
        raise ValueError("aucune pièce à assembler")
    return max(scan, key=lambda a: a.ir_net)


def qualifying(irs: list[float], n_obs: int) -> int:
    """Nombre de pièces dont l'IR dépasse le seuil d'entrée `1/√N`."""
    seuil = entry_threshold(n_obs)
    return sum(1 for i in irs if i > seuil)


# --- La décote, testée hors échantillon par un tiers -------------------------

def implied_second_half_sharpe(full_sharpe: float, years: float,
                               rate: float) -> float:
    """Sharpe attendu sur la seconde moitié d'un échantillon, sous décote.

    Un effet qui décroît au taux `rate` depuis sa publication rend, sur une
    fenêtre postérieure de `years` années, un Sharpe réduit du facteur de
    survie moyen sur la fenêtre. Le module ne connaît pas le Sharpe scindé du
    travail cité ; il publie donc **ce que chaque taux impliquerait**, de
    sorte que la mesure, le jour où elle est lue, tranche sans qu'on puisse
    ajuster le taux après coup.
    """
    if years <= 0.0:
        raise ValueError("years doit être > 0")
    if rate <= 0.0:
        return full_sharpe
    moyen = (1.0 - math.exp(-rate * years)) / (rate * years)
    return full_sharpe * moyen


def decay_ceiling(full_sharpe: float, observed_second_half: float,
                  years: float) -> float:
    """Taux de décroissance maximal compatible avec un Sharpe observé.

    Inversion numérique de la fonction précédente par bissection. Rendu nul si
    la seconde moitié n'est pas plus faible que l'ensemble — auquel cas la
    décote n'est pas seulement bornée, elle est réfutée sur cette fenêtre.
    """
    if observed_second_half >= full_sharpe:
        return 0.0
    lo, hi = 0.0, 5.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if implied_second_half_sharpe(full_sharpe, years, mid) > observed_second_half:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def main() -> None:
    from .report7 import main as report7_main
    report7_main()


if __name__ == "__main__":
    main()
