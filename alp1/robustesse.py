"""L'invariance ne suppose pas la normalité : six lois de prix, un seul résultat.

Pourquoi ce module existe
-------------------------
L'objection est constante et elle est sérieuse : « votre théorème suppose une
loi normale, or les rendements ne sont pas normaux — les queues sont épaisses,
la baisse est bornée et la hausse ne l'est pas ». La première moitié de la
phrase est fausse et la seconde est vraie ; le dépôt doit donc les séparer,
et il ne peut le faire qu'en mesurant.

**Ce que l'identité de Wald exige.** Elle exige que le prix soit une
martingale de carré intégrable et que le temps d'arrêt soit borné. Elle
n'exige **ni normalité, ni symétrie, ni indépendance des amplitudes**. Un
prix à sauts, à queues infiniment épaisses, à volatilité en grappes ou à
baisse plafonnée reste une martingale tant que ses incréments sont centrés,
et le théorème d'arrêt optionnel s'y applique mot pour mot :

    E[R] = (µ · E[τ∧T] − c) / a

Ce module remplace la loi des incréments six fois, à variance par minute
**identique**, et regarde ce qui bouge.

Les six lois, et pourquoi celles-là
-----------------------------------
1. `gauss`      — la référence, celle qu'on accuse d'être supposée.
2. `student5`   — Student à cinq degrés de liberté : kurtosis excédentaire 6,
                  queues épaisses, symétrique. La critique usuelle.
3. `student3`   — Student à trois degrés : la variance existe encore, **le
                  moment d'ordre quatre non**. Le cas limite : si le résultat
                  survit à une kurtosis infinie, il ne doit rien à la normalité.
4. `merton`     — diffusion plus sauts de Poisson **négatifs**, compensés pour
                  rester centrés. C'est la vraie forme d'un indice actions :
                  asymétrie négative, pas positive.
5. `melange`    — volatilité de séance lognormale, tirée une fois par séance :
                  les incréments se groupent en régimes calmes et agités.
6. `plafonnee`  — l'affirmation prise au mot : incrément exponentiel recentré,
                  **borné par le bas à un écart-type, non borné par le haut**.
                  Asymétrie +2, kurtosis excédentaire 6.

La sixième mérite un mot. Elle n'est pas une caricature : c'est exactement
« la baisse est plafonnée, la hausse est illimitée », écrit en loi. Si cette
propriété créait de l'espérance, elle en créerait ici plus que nulle part
ailleurs.

Ce que la mesure trouve, et ce qu'elle ne trouve pas
----------------------------------------------------
Le résultat se lit en trois temps, et le deuxième est celui que personne
n'attend :

1. **Sous prix sans dérive, les six lois rendent `−c/a`**, à l'erreur de
   Monte-Carlo près. La kurtosis infinie n'y fait pas exception, ni la baisse
   plafonnée. L'espérance d'une géométrie ne dépend pas de la forme des
   queues, parce qu'elle ne dépend que du fait que le prix soit centré.
2. **Le dépassement de barrière ne change rien non plus.** On traverse son
   stop, oui — mais on traverse son objectif aussi, et l'arrêt optionnel
   compte les deux. C'est contre-intuitif et c'est mesuré ici sur la loi qui
   saute : le dépassement moyen au stop y est plusieurs fois celui de la
   gaussienne, et l'espérance ne bouge pas.
3. **Ce que la loi déplace, c'est le temps de marché** — donc le seuil. Des
   queues épaisses font toucher les barrières plus tôt, `E[τ∧T]` tombe, et
   `µ* = c/E[τ∧T]` monte. La critique atterrit donc, mais pas où elle visait :
   elle ne réfute pas l'invariance, elle **renchérit le seuil**. C'est le
   résultat du document, une fois de plus, par une autre porte.

Le piège de l'appariement antithétique
--------------------------------------
Quatre des six lois sont symétriques et acceptent le doublage antithétique,
qui divise la variance de simulation. Les deux autres ne l'acceptent pas :
**changer le signe d'un incrément asymétrique change sa loi**, et l'appariement
fabriquerait une symétrie que la loi n'a pas. Le champ `symetrique` porte cette
distinction, un test l'exige, et les erreurs types publiées en tiennent compte.

Les six lois voient en revanche toutes le **même flux de nombres aléatoires** :
chaque trajectoire réamorce un générateur à la même graine, et chaque loi
l'interprète à sa façon. Les écarts entre lois sont donc appariés à la source.
"""

from __future__ import annotations

import math
import zlib
from dataclasses import dataclass
from functools import lru_cache

from .costs import COST_BASE, ES, _norm_ppf
from .mc import Rng
from .report import INDEX_LEVEL, SESSION_MIN, SIGMA_1MIN, Table, num
from .seuil import PLAUSIBLE_DRIFT_PER_HOUR

# --- La géométrie de l'épreuve ---------------------------------------------
#
# Le stop retenu est celui de `sorties.py`, et pour la même raison : à la
# largeur déclarée du document nº 1, une minute de bruit vaut deux stops, si
# bien que la loi des incréments n'a pas le temps de s'exprimer avant que la
# barrière ne soit franchie. À 0,150 % elle a le temps, et c'est la seule
# condition sous laquelle la question posée ici a un sens.

STOP_PCT = 0.150
RR = 2.0
PAS_MIN = 1.0
SEANCE_MIN = int(SESSION_MIN)

#: Trajectoires par loi. Les lois symétriques les doublent par antithétique.
N_PATHS = 24000
SEED = 20260830

#: Taille de l'échantillon d'incréments sur lequel les moments sont mesurés.
N_MOMENTS = 400000

#: La dérive haute du domaine plausible du document nº 1.
DERIVE_HAUTE = PLAUSIBLE_DRIFT_PER_HOUR[1]

#: Combien de verdicts la campagne prononce : six lois, deux dérives. Le seuil
#: de décision est corrigé pour ce nombre, et il faut dire pourquoi. À 5 % et
#: douze tests, la probabilité qu'au moins un écart dépasse deux erreurs types
#: **alors que le théorème tient partout** est de 46 % : publier « réfutée »
#: sur cette base reviendrait à annoncer une découverte au premier faux
#: positif. C'est la faute que le document reproche ailleurs, et la règle qui
#: la corrige est celle qu'il emploie partout — on la lui applique donc à
#: lui-même. Le seuil est **calculé** par Bonferroni, jamais écrit.
N_TESTS = 12
ALPHA_TEST = 0.05
Z_SEUIL = _norm_ppf(1.0 - ALPHA_TEST / (2.0 * N_TESTS))

#: Résolution visée quand on demande combien de décisions il faut pour lire sa
#: propre espérance. Un centième de R, sur une géométrie dont la friction vaut
#: quatre centièmes de R : c'est la précision minimale pour distinguer une
#: espérance nulle d'une espérance qui paie le courtier.
RESOLUTION_R = 0.01
DECISIONS_PAR_AN = 504.0


def stop_points() -> float:
    return STOP_PCT / 100.0 * INDEX_LEVEL


def target_points() -> float:
    return RR * stop_points()


def friction() -> float:
    return COST_BASE.friction_points(ES)


def bruit_par_pas() -> float:
    return SIGMA_1MIN * math.sqrt(PAS_MIN)


# --- Les six lois ----------------------------------------------------------
#
# Chacune rend un incrément **centré et de variance un**. La mise à l'échelle
# par `bruit_par_pas()` est faite une seule fois, au moment de la simulation :
# ainsi aucune loi ne peut se donner une volatilité différente d'une autre, et
# la comparaison porte sur la seule forme.

#: Sauts de Merton — intensité par minute, moyenne et écart-type du saut, en
#: écarts-types de l'incrément de base. Un saut de six sigma vaut 7,5 points,
#: soit 83 % du stop en une minute : c'est l'ordre de grandeur d'un indice sur
#: une publication macroéconomique, et non une caricature.
SAUT_LAMBDA = 0.003
SAUT_MOYENNE = -6.0
SAUT_ECART = 2.0

#: Dispersion logarithmique de la volatilité de séance du mélange.
MELANGE_SIGMA = 0.80


def _gauss(rng: Rng, etat: dict) -> float:
    return rng.gauss()


def _student(nu: int):
    """Student à `nu` degrés, remis à variance un.

    Le tirage passe par la définition : une normale divisée par la racine
    d'un khi-deux réduit. À `nu = 3` la variance existe et vaut trois ; le
    moment d'ordre quatre, lui, diverge — la kurtosis empirique d'un tel
    échantillon n'est donc pas un estimateur, c'est un tirage. Le module le
    dit plutôt que de publier un nombre qui n'existe pas.
    """
    echelle = math.sqrt(nu / (nu - 2.0))

    def f(rng: Rng, etat: dict) -> float:
        z = rng.gauss()
        khi = 0.0
        for _ in range(nu):
            g = rng.gauss()
            khi += g * g
        return z / math.sqrt(khi / nu) / echelle

    return f


def _merton(rng: Rng, etat: dict) -> float:
    """Diffusion plus sauts négatifs compensés, variance totale un.

    La compensation `− λ·m` est ce qui fait de ce prix une martingale : sans
    elle, un processus à sauts négatifs dériverait à la baisse et le théorème
    ne s'appliquerait plus — mais pour une raison qui n'a rien à voir avec ses
    queues.
    """
    var_saut = SAUT_LAMBDA * (SAUT_MOYENNE ** 2 + SAUT_ECART ** 2)
    diffusion = math.sqrt(max(1.0 - var_saut, 0.0))
    x = diffusion * rng.gauss() - SAUT_LAMBDA * SAUT_MOYENNE
    if rng.uniform() < SAUT_LAMBDA:
        x += SAUT_MOYENNE + SAUT_ECART * rng.gauss()
    return x


def _melange(rng: Rng, etat: dict) -> float:
    """Volatilité de séance lognormale d'espérance un, tirée une fois par séance."""
    v = etat.get("v")
    if v is None:
        s = MELANGE_SIGMA
        v = math.exp(s * rng.gauss() - 0.5 * s * s)
        etat["v"] = v
    return math.sqrt(v) * rng.gauss()


def _plafonnee(rng: Rng, etat: dict) -> float:
    """Exponentielle recentrée : plancher à −1, plafond nul.

    C'est l'affirmation « la baisse est plafonnée, la hausse est illimitée »
    écrite en loi de probabilité. Moyenne nulle, variance un, asymétrie +2,
    kurtosis excédentaire 6, et un incrément qui ne peut jamais descendre
    au-dessous d'un écart-type.
    """
    u = max(rng.uniform(), 1e-300)
    return -math.log(u) - 1.0


@dataclass(frozen=True)
class Loi:
    """Une loi d'incrément, sa fonction de tirage et ce qu'on en dit."""

    cle: str
    nom: str
    description: str
    fn: object
    symetrique: bool
    court: str = ""
    kurtosis_finie: bool = True
    par_seance: bool = False


def _graine(cle: str) -> int:
    """La graine d'une loi, dérivée de son nom **de façon reproductible**.

    Le `hash` intégré de Python est randomisé par processus depuis la 3.3 :
    deux exécutions du dépôt en tiraient deux graines différentes, donc deux
    jeux de chiffres différents pour toute la partie XIV. Rien ne le
    signalait — les nombres restaient plausibles et les tolérances des tests
    les absorbaient — jusqu'à ce qu'un contrôle de borne à 10⁻⁶ tombe d'un
    côté puis de l'autre. Un CRC de la chaîne rend la même valeur partout et
    toujours, ce qu'exige la règle du dépôt sur l'aléa.
    """
    return SEED ^ (zlib.crc32(cle.encode("utf-8")) & 0xFFFF)


def lois() -> tuple[Loi, ...]:
    return (
        Loi("gauss", "Gaussienne",
            "la loi qu'on accuse le théorème de supposer",
            _gauss, symetrique=True, court="normale"),
        Loi("student5", "Student, 5 degrés",
            "queues épaisses, symétrique, kurtosis excédentaire 6",
            _student(5), symetrique=True, court="Student 5"),
        Loi("student3", "Student, 3 degrés",
            "la variance existe, le moment d'ordre quatre non",
            _student(3), symetrique=True, court="Student 3",
            kurtosis_finie=False),
        Loi("merton", "Sauts de Merton",
            "diffusion plus sauts négatifs compensés : l'asymétrie d'un indice",
            _merton, symetrique=False, court="sauts"),
        Loi("melange", "Volatilité en grappes",
            "volatilité de séance lognormale, régimes calmes et agités",
            _melange, symetrique=True, court="grappes", par_seance=True),
        Loi("plafonnee", "Baisse plafonnée",
            "plancher à un écart-type, hausse non bornée : l'affirmation au mot",
            _plafonnee, symetrique=False, court="plancher"),
    )


# --- Les moments empiriques ------------------------------------------------


@dataclass(frozen=True)
class Moments:
    cle: str
    moyenne: float
    ecart_type: float
    asymetrie: float
    kurtosis: float          # excédentaire
    borne_basse: float       # le pire incrément observé, en écarts-types


@lru_cache(maxsize=None)
def moments(n: int = N_MOMENTS) -> tuple[Moments, ...]:
    """Les quatre premiers moments de chaque loi, mesurés et non déclarés.

    Rien n'oblige une loi écrite à la main à être centrée et réduite ; c'est
    précisément ce qu'il faut vérifier avant de comparer six simulations, et
    un test le vérifie.
    """
    out = []
    for loi in lois():
        rng = Rng(_graine(loi.cle))
        s1 = s2 = s3 = s4 = 0.0
        pire = math.inf
        etat: dict = {}
        for i in range(n):
            if loi.par_seance and i % SEANCE_MIN == 0:
                etat = {}
            x = loi.fn(rng, etat)
            pire = min(pire, x)
            s1 += x
            s2 += x * x
            s3 += x * x * x
            s4 += x * x * x * x
        m = s1 / n
        v = s2 / n - m * m
        sd = math.sqrt(max(v, 1e-30))
        m3 = s3 / n - 3.0 * m * s2 / n + 2.0 * m ** 3
        m4 = s4 / n - 4.0 * m * s3 / n + 6.0 * m * m * s2 / n - 3.0 * m ** 4
        out.append(Moments(loi.cle, m, sd, m3 / sd ** 3, m4 / sd ** 4 - 3.0,
                           pire))
    return tuple(out)


#: Les seuils, en écarts-types, sur lesquels les deux queues sont comptées.
SEUILS_QUEUE = tuple(0.25 * k for k in range(1, 25))


@lru_cache(maxsize=None)
def queues(n: int = N_MOMENTS) -> dict[str, tuple[tuple[float, float, float], ...]]:
    """Pour chaque loi, `P(X ≤ −x)` et `P(X ≥ +x)` sur une grille d'écarts-types.

    C'est la seule façon honnête de montrer « les queues ne sont pas les mêmes » :
    en les comptant. Une densité tracée à la main dirait ce qu'on veut ; une
    fréquence empirique dit ce que la loi fait. Les deux queues sont comptées
    séparément parce que c'est précisément leur écart qui est en cause.
    """
    out: dict[str, tuple[tuple[float, float, float], ...]] = {}
    for loi in lois():
        rng = Rng(_graine(loi.cle))
        bas = [0] * len(SEUILS_QUEUE)
        haut = [0] * len(SEUILS_QUEUE)
        etat: dict = {}
        for i in range(n):
            if loi.par_seance and i % SEANCE_MIN == 0:
                etat = {}
            x = loi.fn(rng, etat)
            for k, seuil in enumerate(SEUILS_QUEUE):
                if x <= -seuil:
                    bas[k] += 1
                elif x >= seuil:
                    haut[k] += 1
                else:
                    break
        out[loi.cle] = tuple((seuil, bas[k] / n, haut[k] / n)
                             for k, seuil in enumerate(SEUILS_QUEUE))
    return out


# --- La simulation ---------------------------------------------------------


@dataclass(frozen=True)
class Mesure:
    """Ce qu'une loi rend, à une dérive donnée."""

    cle: str
    n: int
    p_target: float
    p_stop: float
    p_cloture: float
    exposition: float        # E[τ∧T], en minutes
    esperance: float         # E[R] simulée
    ecart_type: float        # écart-type de R, sur une décision
    erreur_type: float       # erreur type de E[R]
    wald: float              # (µ·E[τ∧T] − c)/a
    depassement: float       # dépassement moyen du stop, en points, quand stoppé
    queue: float             # quantile 1 % de R
    seuil: float             # µ* = c/E[τ∧T], en points par heure


def _trajectoire(loi: Loi, rng: Rng, mu: float, sig: float, signe: float,
                 a: float, b: float) -> tuple[int, float]:
    """Un aller simple jusqu'à la première barrière, ou jusqu'à la clôture.

    Le prix de sortie est celui **atteint**, jamais celui de la barrière : un
    stop franchi dans le pas est constaté au-delà. C'est ce dépassement que la
    critique des queues épaisses vise, et c'est pour cela qu'il est mesuré
    plutôt que gommé.
    """
    x = 0.0
    etat: dict = {}
    for i in range(1, SEANCE_MIN + 1):
        x += mu + sig * signe * loi.fn(rng, etat)
        if x <= -a or x >= b:
            return i, x
    return SEANCE_MIN, x


@lru_cache(maxsize=None)
def mesurer(drift_per_hour: float, n_paths: int = N_PATHS) -> tuple[Mesure, ...]:
    """Applique la même géométrie aux six lois, sur le même flux d'aléa."""
    a, b, c = stop_points(), target_points(), friction()
    sig, mu = bruit_par_pas(), drift_per_hour / 60.0 * PAS_MIN
    out = []
    for loi in lois():
        signes = (1.0, -1.0) if loi.symetrique else (1.0,)
        n = 0
        s1 = s2 = 0.0
        n_t = n_s = 0
        tau = 0.0
        dep = 0.0
        rs: list[float] = []
        for k in range(n_paths):
            for signe in signes:
                # Chaque loi réamorce à la même graine : le flux d'aléa est
                # commun, seule son interprétation change.
                rng = Rng(SEED + k * 7919)
                i, x = _trajectoire(loi, rng, mu, sig, signe, a, b)
                r = (x - c) / a
                n += 1
                s1 += r
                s2 += r * r
                tau += i * PAS_MIN
                rs.append(r)
                if x >= b:
                    n_t += 1
                elif x <= -a:
                    n_s += 1
                    dep += (-a) - x
        m = s1 / n
        v = max(s2 / n - m * m, 0.0)
        e = tau / n
        rs.sort()
        out.append(Mesure(
            cle=loi.cle, n=n,
            p_target=n_t / n, p_stop=n_s / n,
            p_cloture=1.0 - (n_t + n_s) / n,
            exposition=e, esperance=m,
            ecart_type=math.sqrt(v), erreur_type=math.sqrt(v / n),
            wald=(drift_per_hour / 60.0 * e - c) / a,
            depassement=dep / n_s if n_s else 0.0,
            queue=rs[max(int(0.01 * len(rs)) - 1, 0)],
            seuil=c / (e / 60.0) if e > 0.0 else math.inf,
        ))
    return tuple(out)


def _par_cle(drift: float) -> dict[str, Mesure]:
    return {m.cle: m for m in mesurer(drift)}


def _verdict(m: Mesure) -> tuple[float, str]:
    """L'écart à la prédiction de Wald, en erreurs types, et son verdict.

    Le verdict est **calculé**, contre le seuil corrigé de la campagne et non
    contre le deux usuel. Au-delà, la ligne dirait que le théorème ne tient pas
    sous cette loi, et il faudrait l'écrire.
    """
    z = (m.esperance - m.wald) / m.erreur_type if m.erreur_type > 0 else 0.0
    return z, "compatible" if abs(z) < Z_SEUIL else "réfutée"


# --- Les tables ------------------------------------------------------------


def table_lois() -> Table:
    """Les six lois et leurs moments, mesurés sur le tirage lui-même."""
    rows = []
    mm = {x.cle: x for x in moments()}
    for loi in lois():
        x = mm[loi.cle]
        kurt = num(x.kurtosis, 2) if loi.kurtosis_finie else "infinie"
        rows.append([
            loi.nom, loi.description,
            num(x.ecart_type, 3),
            num(x.asymetrie, 2, signed=True),
            kurt,
            num(x.borne_basse, 2, signed=True),
        ])
    return Table(
        "robu_lois",
        "Les six lois d'incrément, à variance par minute identique.",
        ["Loi", "Ce qu'elle porte", "Écart-type", "Asymétrie",
         "Kurtosis excéd.", "Pire incrément"],
        rows,
        note=("Toutes les lois sont centrées et ramenées à une variance de un : "
              "la colonne d'écart-type le vérifie plutôt que de le supposer, et "
              "c'est ce qui autorise la comparaison. Le « pire incrément » est "
              "le minimum observé sur " + num(N_MOMENTS / 1000.0, 0) + " mille "
              "tirages, en écarts-types ; la loi à baisse plafonnée ne "
              "descend jamais au-dessous de −1, par construction. La kurtosis "
              "de la Student à trois degrés est écrite « infinie » et non "
              "estimée : son moment d'ordre quatre diverge, si bien qu'un "
              "nombre publié là ne serait pas une mesure mais un tirage."),
        wrap_last=True, wrap_cols=[1],
    )


def table_invariance() -> Table:
    """Sous prix sans dérive, les six lois rendent la même espérance."""
    a, c = stop_points(), friction()
    rows = []
    for loi in lois():
        m = _par_cle(0.0)[loi.cle]
        z, verdict = _verdict(m)
        rows.append([
            loi.nom,
            num(m.p_target * 100.0, 1, " %"),
            num(m.p_stop * 100.0, 1, " %"),
            num(m.exposition, 1),
            num(m.esperance, 4, signed=True),
            num(m.wald, 4, signed=True),
            num(z, 2, signed=True),
            verdict,
        ])
    return Table(
        "robu_invariance",
        "L'espérance d'une géométrie sous prix sans dérive, loi par loi.",
        ["Loi", "p(objectif)", "p(stop)", "E[τ∧T] (min)", "E[R] simulée",
         "−c/a prédit", "Écart (erreurs types)", "Verdict"],
        rows,
        note=("La prédiction est la même pour les six lignes : à dérive "
              "nulle, l'identité de Wald donne "
              "E[R] = −c/a = " + num(-c / a, 4, signed=True) + " R, quelle que "
              "soit la loi des incréments. La colonne de verdict est "
              "**calculée** contre " + num(Z_SEUIL, 2) + " erreurs types — le "
              "seuil de Bonferroni des " + num(N_TESTS, 0) + " verdicts de la "
              "campagne, et non le deux usuel. La correction n'est pas une "
              "indulgence : à " + num(ALPHA_TEST * 100.0, 0) + " % et "
              + num(N_TESTS, 0) + " tests, la probabilité qu'au moins un écart "
              "dépasse deux erreurs types **alors que le théorème tient "
              "partout** vaut "
              + num((1.0 - (1.0 - ALPHA_TEST) ** N_TESTS) * 100.0, 0)
              + " %, et publier « réfutée » sur cette base reviendrait à "
                "annoncer une découverte au premier faux positif. Les "
                "probabilités de barrière, elles, changent d'une loi à "
                "l'autre : c'est attendu, et cela ne déplace pas "
                "l'espérance."),
        wrap_last=True,
    )


def table_derive() -> Table:
    """Sous dérive déclarée, chaque loi retombe sur sa propre prédiction."""
    rows = []
    for loi in lois():
        m = _par_cle(DERIVE_HAUTE)[loi.cle]
        z, verdict = _verdict(m)
        rows.append([
            loi.nom,
            num(m.exposition, 1),
            num(m.esperance, 4, signed=True),
            num(m.wald, 4, signed=True),
            num(z, 2, signed=True),
            verdict,
        ])
    return Table(
        "robu_derive",
        "Sous une dérive de " + num(DERIVE_HAUTE, 1) + " point par heure, "
        "la borne haute du domaine plausible.",
        ["Loi", "E[τ∧T] (min)", "E[R] simulée", "Prédiction de Wald",
         "Écart (erreurs types)", "Verdict"],
        rows,
        note=("La prédiction n'est plus commune aux six lignes : elle vaut "
              "(µ·E[τ∧T] − c)/a, et `E[τ∧T]` dépend de la loi. C'est là, et "
              "nulle part ailleurs, que la forme des queues entre dans le "
              "résultat — par le temps de marché, jamais par un avantage "
              "propre."),
        wrap_last=True,
    )


def table_deplacement() -> Table:
    """Ce que la loi déplace vraiment : le temps, le seuil, et la queue."""
    ref = _par_cle(0.0)["gauss"]
    rows = []
    for loi in lois():
        m = _par_cle(0.0)[loi.cle]
        rows.append([
            loi.nom,
            num(m.exposition, 1),
            num(m.seuil, 3),
            num((m.seuil / ref.seuil - 1.0) * 100.0, 1, " %", signed=True),
            num(m.depassement, 3),
            num(m.ecart_type, 3),
            num(m.queue, 3, signed=True),
        ])
    return Table(
        "robu_deplacement",
        "Ce que la forme des queues déplace, une fois l'espérance écartée.",
        ["Loi", "E[τ∧T] (min)", "µ* (pt/h)", "Écart de seuil",
         "Dépassement au stop (pts)", "Écart-type de R", "Quantile 1 % de R"],
        rows,
        note=("Le dépassement est ce dont on franchit son stop dans le pas où "
              "on le franchit. La loi qui saute le multiplie par "
              + num(_par_cle(0.0)["merton"].depassement / ref.depassement, 1)
              + " par rapport à la gaussienne, et son espérance ne bouge "
                "pas : on traverse son stop, mais on traverse son "
                "objectif aussi, et l'arrêt optionnel compte les deux. Ce que "
                "les queues emportent vraiment tient dans les trois dernières "
                "colonnes : le seuil de rentabilité, la dispersion, et la "
                "queue de perte — c'est-à-dire ce qu'il faut de marché, et ce "
                "qu'il faut de capital, jamais ce qu'on gagne."),
        wrap_last=True,
    )


# --- La famille continue des surfaces --------------------------------------
#
# Les six lois nommées répondent à la question « le théorème tient-il ? ». Elles
# ne répondent pas à « de combien la forme des queues déplace-t-elle le
# seuil ? », parce qu'un axe catégoriel ne se dérive pas. Il faut donc une
# famille **continue** d'épaisseurs de queue, à variance constante, et le
# mélange d'échelles à deux points la donne pour un tirage de plus par pas :
# avec probabilité `p` la minute est agitée, sinon elle est calme, et les deux
# variances sont liées par `E[V] = 1`. La kurtosis excédentaire vaut alors
# `3·(E[V²] − 1)` — une formule, pas une mesure.
#
# **Toutes les cellules des surfaces voient le même flux d'aléa** : la graine
# ne dépend que de l'indice de trajectoire, jamais de la cellule. Le bruit de
# Monte-Carlo est donc commun à la grille entière, ce qui laisse le relief
# lisse : les cellules voisines diffèrent par leur paramètre, pas par leur
# tirage. C'est la même raison qui fait apparier les trajectoires ailleurs
# dans le dépôt, et il faut le dire, parce qu'une surface lisse obtenue
# autrement serait un lissage.

MIX_P = 0.05
SURF_V2 = (1.0, 3.0, 6.0, 10.0, 16.0)
SURF_DERIVE = (0.0, 0.8, 1.6, 2.4, 3.2)
SURF_STOP_PCT = (0.050, 0.075, 0.100, 0.150, 0.225)
N_SURFACE = 4000


def kurtosis_mixte(v2: float, p: float = MIX_P) -> float:
    """La kurtosis excédentaire du mélange, par sa formule."""
    v1 = (1.0 - p * v2) / (1.0 - p)
    return 3.0 * ((1.0 - p) * v1 * v1 + p * v2 * v2 - 1.0)


def _mixte(v2: float, p: float = MIX_P):
    """Mélange d'échelles à deux points, de variance un."""
    v1 = (1.0 - p * v2) / (1.0 - p)
    if v1 < 0.0:
        raise ValueError("mélange impossible : la variance calme serait négative")
    r1, r2 = math.sqrt(v1), math.sqrt(v2)

    def f(rng: Rng, etat: dict) -> float:
        agitee = rng.uniform() < p
        return (r2 if agitee else r1) * rng.gauss()

    return f


@lru_cache(maxsize=None)
def cellule(v2: float, drift_per_hour: float, stop_pct: float,
            n_paths: int = N_SURFACE) -> tuple[float, float]:
    """`(E[R], E[τ∧T])` pour une épaisseur de queue, une dérive, un stop."""
    a = stop_pct / 100.0 * INDEX_LEVEL
    b, c = RR * a, friction()
    sig, mu = bruit_par_pas(), drift_per_hour / 60.0 * PAS_MIN
    loi = Loi("mix", "mélange", "", _mixte(v2), symetrique=True)
    s1 = tau = 0.0
    n = 0
    for k in range(n_paths):
        for signe in (1.0, -1.0):
            rng = Rng(SEED + k * 7919)
            i, x = _trajectoire(loi, rng, mu, sig, signe, a, b)
            s1 += (x - c) / a
            tau += i * PAS_MIN
            n += 1
    return s1 / n, tau / n


def surface_esperance() -> list[list[float]]:
    """E[R] sur le plan (épaisseur de queue, dérive), au stop de référence.

    Les deux axes sont écrits en ordre **décroissant** : en projection
    isométrique le coin `(0, 0)` est le plus éloigné, et c'est là que le
    maximum doit tomber pour que le relief monte vers l'horizon.
    """
    return [[cellule(v2, d, STOP_PCT)[0]
             for d in sorted(SURF_DERIVE, reverse=True)]
            for v2 in sorted(SURF_V2, reverse=True)]


def surface_seuil() -> list[list[float]]:
    """µ* sur le plan (épaisseur de queue, largeur de stop), à dérive nulle."""
    c = friction()
    return [[c / (cellule(v2, 0.0, pct)[1] / 60.0)
             for pct in sorted(SURF_STOP_PCT)]
            for v2 in sorted(SURF_V2)]


def decisions_pour(sd: float, resolution: float = RESOLUTION_R) -> float:
    """Combien de décisions pour lire une espérance à `resolution` près.

    C'est la formule de l'intervalle de confiance retournée : `n = (z·σ/ε)²`.
    Elle ne suppose rien de la loi de `R` sinon que sa variance existe et que
    le théorème central limite s'applique à sa moyenne — et c'est précisément
    ce qui rend le nombre optimiste sous une queue épaisse, où la convergence
    vers la normale est lente. Les valeurs publiées sont donc des **planchers**.
    """
    z = _norm_ppf(1.0 - ALPHA_TEST / 2.0)
    return (z * sd / resolution) ** 2


def table_echantillon() -> Table:
    """Ce qu'il faut de décisions pour lire sa propre espérance, loi par loi."""
    rows = []
    for loi in lois():
        m = _par_cle(0.0)[loi.cle]
        n = decisions_pour(m.ecart_type)
        rows.append([
            loi.nom,
            num(m.ecart_type, 3),
            num(n / 1000.0, 1) + " k",
            num(n / DECISIONS_PAR_AN, 0),
            num(m.n / 1000.0, 0) + " k",
            num(RESOLUTION_R * math.sqrt(n / m.n), 3),
        ])
    return Table(
        "robu_echantillon",
        "Le prix, en décisions, d'une espérance lue au centième de R.",
        ["Loi", "Écart-type de R", "Décisions requises", "Années à "
         + num(DECISIONS_PAR_AN, 0) + " décisions", "Décisions simulées",
         "Résolution atteinte (R)"],
        rows,
        note=("La simulation elle-même n'atteint pas le centième de R : la "
              "dernière colonne dit ce qu'elle résout vraiment, et c'est "
              + num(min(RESOLUTION_R * math.sqrt(decisions_pour(
                  _par_cle(0.0)[l.cle].ecart_type) / _par_cle(0.0)[l.cle].n)
                  for l in lois()), 3) + " à "
              + num(max(RESOLUTION_R * math.sqrt(decisions_pour(
                  _par_cle(0.0)[l.cle].ecart_type) / _par_cle(0.0)[l.cle].n)
                  for l in lois()), 3) + " R. Ce n'est pas un défaut de la "
              "simulation, c'est le sujet. Un opérateur qui veut savoir si "
              "son espérance vaut zéro ou vaut la friction affronte le même "
              "mur, avec une décision par heure au lieu de vingt-quatre mille "
              "en deux minutes. Le nombre publié est un **plancher** : il "
              "suppose la moyenne déjà normale, ce que la Student à trois "
              "degrés met bien plus longtemps à devenir."),
        wrap_last=True,
    )


TABLES = (table_lois, table_invariance, table_derive, table_deplacement,
          table_echantillon)


def all_tables() -> dict[str, Table]:
    return {t().key: t() for t in TABLES}


def values() -> dict[str, str]:
    z0 = _par_cle(0.0)
    zd = _par_cle(DERIVE_HAUTE)
    ref = z0["gauss"]
    a, c = stop_points(), friction()
    pires = max(abs(_verdict(m)[0]) for m in z0.values())
    pires_d = max(abs(_verdict(m)[0]) for m in zd.values())
    seuils = [m.seuil for m in z0.values()]
    mm = {x.cle: x for x in moments()}
    return {
        "r_stop_pct": num(STOP_PCT, 3),
        "r_stop_pts": num(a, 2),
        "r_rr": num(RR, 0),
        "r_friction": num(c, 2),
        "r_lois": num(len(lois()), 0),
        "r_paths": num(N_PATHS / 1000.0, 0),
        "r_prediction": num(-c / a, 4, signed=True),
        "r_ecart_max": num(pires, 2),
        "r_ecart_max_derive": num(pires_d, 2),
        "r_z_seuil": num(Z_SEUIL, 2),
        "r_tests": num(N_TESTS, 0),
        "r_faux_positif": num((1.0 - (1.0 - ALPHA_TEST) ** N_TESTS) * 100.0, 0),
        "r_decisions_gauss": num(decisions_pour(ref.ecart_type) / 1000.0, 1),
        "r_annees_gauss": num(decisions_pour(ref.ecart_type) / DECISIONS_PAR_AN, 0),
        "r_resolution": num(RESOLUTION_R, 2),
        "r_resolution_atteinte": num(
            RESOLUTION_R * math.sqrt(decisions_pour(ref.ecart_type) / ref.n), 3),
        "r_derive_haute": num(DERIVE_HAUTE, 1),
        "r_tau_gauss": num(ref.exposition, 1),
        "r_tau_student3": num(z0["student3"].exposition, 1),
        "r_seuil_gauss": num(ref.seuil, 3),
        "r_seuil_max": num(max(seuils), 3),
        "r_seuil_ecart": num((max(seuils) / min(seuils) - 1.0) * 100.0, 1),
        "r_dep_gauss": num(ref.depassement, 3),
        "r_dep_merton": num(z0["merton"].depassement, 3),
        "r_dep_facteur": num(z0["merton"].depassement / ref.depassement, 1),
        "r_queue_gauss": num(ref.queue, 3, signed=True),
        "r_queue_merton": num(z0["merton"].queue, 3, signed=True),
        "r_sd_gauss": num(ref.ecart_type, 3),
        "r_sd_merton": num(z0["merton"].ecart_type, 3),
        "r_asym_merton": num(mm["merton"].asymetrie, 2, signed=True),
        "r_queue_facteur": num(_rapport_queues("merton", 3.0), 1),
        "r_queue_sigma": num(3.0, 0),
        "r_asym_plafonnee": num(mm["plafonnee"].asymetrie, 2, signed=True),
        "r_kurt_student5": num(mm["student5"].kurtosis, 1),
        "r_plancher_plafonnee": num(mm["plafonnee"].borne_basse, 2, signed=True),
        "r_esp_plafonnee": num(z0["plafonnee"].esperance, 4, signed=True),
        "r_esp_merton": num(z0["merton"].esperance, 4, signed=True),
        "r_saut_pts": num(abs(SAUT_MOYENNE) * bruit_par_pas(), 1),
        "r_saut_part": num(abs(SAUT_MOYENNE) * bruit_par_pas() / a * 100.0, 0),
        "r_saut_seance": num(SAUT_LAMBDA * SEANCE_MIN, 2),
        "r_surf_kurt_max": num(kurtosis_mixte(max(SURF_V2)), 1),
        "r_surf_stop_min": num(min(SURF_STOP_PCT), 3),
        "r_surf_stop_max": num(max(SURF_STOP_PCT), 3),
        "r_surf_seuil_geo": num(_surf_facteur()[0], 1),
        "r_surf_seuil_queue": num(_surf_facteur()[1], 2),
        "r_surf_domine": num(_surf_facteur()[0] / _surf_facteur()[1], 1),
        "r_surf_esp_nulle": num(_surf_plat(), 4, signed=True),
        "r_surf_esp_etendue": num(_surf_etendue(), 4),
    }


def _rapport_queues(cle: str, sigma: float) -> float:
    """Combien de fois une loi tombe plus à gauche qu'à droite, à `sigma`.

    Le chiffre est lu sur le comptage, jamais écrit dans une phrase : c'est le
    genre d'affirmation qui survit dix ans à la mesure qui l'a produite.
    """
    for x, bas, haut in queues()[cle]:
        if abs(x - sigma) < 1e-9:
            return bas / haut if haut else math.inf
    raise KeyError(f"seuil {sigma} absent de la grille")


def _surf_facteur() -> tuple[float, float]:
    """De combien la géométrie déplace le seuil, de combien les queues.

    Les deux rapports sont lus sur la **même** surface, et sur ses arêtes : le
    long de l'axe du stop à queue la plus fine, et le long de l'axe des queues
    au stop le plus serré. Chacun est donc le déplacement maximal que son axe
    autorise, ce qui rend la comparaison des deux honnête.
    """
    z = surface_seuil()
    geo = z[0][0] / z[0][-1]
    queue = z[0][0] / z[-1][0]
    return geo, queue


def _surf_plat() -> float:
    """L'espérance moyenne le long de l'axe des queues, à dérive nulle."""
    z = surface_esperance()
    col = [ligne[-1] for ligne in z]      # dernière colonne : dérive nulle
    return sum(col) / len(col)


def _surf_etendue() -> float:
    """L'étendue de cette même colonne : ce que les queues y font varier."""
    z = surface_esperance()
    col = [ligne[-1] for ligne in z]
    return max(col) - min(col)


def main() -> None:
    for t in TABLES:
        print(t().to_text())
        print()


if __name__ == "__main__":
    main()
