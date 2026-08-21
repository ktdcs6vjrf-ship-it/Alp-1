"""Modèle de Markov caché gaussien : estimation, décodage, et sa loi nulle.

Le HMM est l'outil standard de détection de régime : deux ou trois états
cachés, une émission gaussienne par état, une matrice de transition. Il est
utilisé pour ce que le papier appelle en section 11 le conditionnement de
régime — séparer les périodes où le gamma des teneurs amortit le prix de
celles où il l'amplifie — et il est, dans cet usage, le plus dangereux des
instruments de la boîte.

La raison tient en une phrase : **l'algorithme de Baum-Welch converge
toujours**. Appliqué à une série sans le moindre régime, il produit deux
états, une matrice de transition persistante, un chemin de Viterbi net, et un
gain de vraisemblance qui paraît décisif. Rien dans la sortie ne signale
l'absence de structure. Le module fournit donc, à côté de l'estimation, les
trois quantités qui la rendent réfutable :

* la **séparabilité** `d′ = |µ₁ − µ₂|/σ`, seule grandeur qui décide si deux
  régimes sont distinguables — et le taux d'erreur de Bayes `Φ(−d′/2)` qui en
  découle, borne inférieure de toute classification, si fine soit-elle ;
* le **nombre d'observations** nécessaire pour que la séparation soit
  détectable, qui croît en `1/d′²` ;
* la **loi nulle du gain de vraisemblance**, à obtenir par simulation parce
  que le test du rapport de vraisemblance n'est pas χ² ici : ajouter un état
  place le paramètre à la frontière de son domaine, et la théorie standard
  ne s'applique pas.

Sans ces trois quantités, un régime détecté n'est pas un résultat.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .costs import _norm_ppf, norm_cdf

_LOG_2PI = math.log(2.0 * math.pi)
_FLOOR = 1e-300


# --- Le modèle --------------------------------------------------------------


@dataclass(frozen=True)
class GaussianHMM:
    """HMM à émissions gaussiennes.

    `start[i]` probabilité initiale de l'état `i`, `trans[i][j]` probabilité
    de passer de `i` à `j`, `means[i]` et `sds[i]` l'émission de l'état `i`.
    """

    start: tuple[float, ...]
    trans: tuple[tuple[float, ...], ...]
    means: tuple[float, ...]
    sds: tuple[float, ...]

    def __post_init__(self) -> None:
        n = len(self.means)
        if len(self.sds) != n or len(self.start) != n or len(self.trans) != n:
            raise ValueError("dimensions incohérentes")
        if any(len(row) != n for row in self.trans):
            raise ValueError("la matrice de transition doit être carrée")
        if any(s <= 0 for s in self.sds):
            raise ValueError("les écarts-types doivent être > 0")
        if abs(sum(self.start) - 1.0) > 1e-8:
            raise ValueError("start doit sommer à 1")
        for row in self.trans:
            if abs(sum(row) - 1.0) > 1e-8:
                raise ValueError("chaque ligne de trans doit sommer à 1")

    @property
    def n_states(self) -> int:
        return len(self.means)

    def emission(self, state: int, x: float) -> float:
        mu, sd = self.means[state], self.sds[state]
        z = (x - mu) / sd
        return math.exp(-0.5 * z * z) / (sd * math.sqrt(2.0 * math.pi))

    # --- propriétés de la chaîne ---------------------------------------

    def stationary(self, tol: float = 1e-14, max_iter: int = 100_000) -> tuple[float, ...]:
        """Distribution stationnaire, par itération de la puissance.

        C'est la fréquence d'occupation de long terme de chaque régime — la
        seule quantité de la chaîne qui soit comparable à une statistique
        descriptive observable, et donc le premier contrôle de plausibilité
        d'un modèle ajusté.
        """
        n = self.n_states
        v = [1.0 / n] * n
        for _ in range(max_iter):
            nxt = [sum(v[i] * self.trans[i][j] for i in range(n)) for j in range(n)]
            total = sum(nxt)
            nxt = [x / total for x in nxt]
            if max(abs(a - b) for a, b in zip(v, nxt)) < tol:
                return tuple(nxt)
            v = nxt
        return tuple(v)

    def expected_sojourn(self, state: int) -> float:
        """Durée moyenne de séjour dans un état : `1/(1 − a_ii)`, en périodes.

        La loi de séjour d'un HMM est **géométrique par construction**. C'est
        une contrainte du modèle, pas une observation : un régime de marché
        dont la durée serait, disons, unimodale autour de dix jours ne peut
        pas être représenté par un HMM à un état, quel que soit l'ajustement.
        """
        a = self.trans[state][state]
        return math.inf if a >= 1.0 else 1.0 / (1.0 - a)

    @property
    def n_free_parameters(self) -> int:
        """Paramètres libres : `n(n−1)` transitions + `2n` émissions + `n−1` initiaux.

        Deux états : 7. Trois : 14. Quatre : 23. C'est la croissance
        quadratique qui condamne les modèles à beaucoup d'états sur des
        historiques courts, et que ni l'AIC ni le BIC ne pardonnent.
        """
        n = self.n_states
        return n * (n - 1) + 2 * n + (n - 1)


# --- Vraisemblance et inférence --------------------------------------------


def forward_backward(model: GaussianHMM, obs: list[float]
                     ) -> tuple[float, list[list[float]], list[list[list[float]]]]:
    """Passe avant-arrière avec mise à l'échelle.

    Retourne la log-vraisemblance, les probabilités a posteriori d'état
    `γ[t][i]`, et les probabilités de transition a posteriori `ξ[t][i][j]`.
    La mise à l'échelle à chaque pas évite le sous-débit qui rend une
    implémentation naïve inutilisable au-delà de quelques centaines de points.
    """
    if not obs:
        raise ValueError("séquence vide")
    n, T = model.n_states, len(obs)

    alpha = [[0.0] * n for _ in range(T)]
    scale = [0.0] * T
    for i in range(n):
        alpha[0][i] = model.start[i] * model.emission(i, obs[0])
    scale[0] = sum(alpha[0]) or _FLOOR
    alpha[0] = [a / scale[0] for a in alpha[0]]
    for t in range(1, T):
        for j in range(n):
            acc = sum(alpha[t - 1][i] * model.trans[i][j] for i in range(n))
            alpha[t][j] = acc * model.emission(j, obs[t])
        scale[t] = sum(alpha[t]) or _FLOOR
        alpha[t] = [a / scale[t] for a in alpha[t]]

    beta = [[0.0] * n for _ in range(T)]
    beta[T - 1] = [1.0] * n
    for t in range(T - 2, -1, -1):
        for i in range(n):
            beta[t][i] = sum(model.trans[i][j] * model.emission(j, obs[t + 1])
                             * beta[t + 1][j] for j in range(n)) / scale[t + 1]

    gamma = [[0.0] * n for _ in range(T)]
    for t in range(T):
        total = sum(alpha[t][i] * beta[t][i] for i in range(n)) or _FLOOR
        for i in range(n):
            gamma[t][i] = alpha[t][i] * beta[t][i] / total

    xi = [[[0.0] * n for _ in range(n)] for _ in range(T - 1)]
    for t in range(T - 1):
        total = 0.0
        for i in range(n):
            for j in range(n):
                v = (alpha[t][i] * model.trans[i][j]
                     * model.emission(j, obs[t + 1]) * beta[t + 1][j])
                xi[t][i][j] = v
                total += v
        total = total or _FLOOR
        for i in range(n):
            for j in range(n):
                xi[t][i][j] /= total

    loglik = sum(math.log(max(s, _FLOOR)) for s in scale)
    return loglik, gamma, xi


def log_likelihood(model: GaussianHMM, obs: list[float]) -> float:
    return forward_backward(model, obs)[0]


def viterbi(model: GaussianHMM, obs: list[float]) -> list[int]:
    """Chemin d'états le plus probable, en log pour la stabilité.

    Le chemin de Viterbi est **toujours net**, y compris sur du bruit pur :
    c'est un argmax, il ne rapporte aucune incertitude. Lire un régime sur ce
    chemin sans regarder `γ[t]` — la probabilité a posteriori, elle
    informative — est l'erreur usuelle d'usage du modèle.
    """
    if not obs:
        raise ValueError("séquence vide")
    n, T = model.n_states, len(obs)

    def log_em(i: int, x: float) -> float:
        sd = model.sds[i]
        z = (x - model.means[i]) / sd
        return -0.5 * z * z - math.log(sd) - 0.5 * _LOG_2PI

    delta = [[-math.inf] * n for _ in range(T)]
    psi = [[0] * n for _ in range(T)]
    for i in range(n):
        delta[0][i] = math.log(max(model.start[i], _FLOOR)) + log_em(i, obs[0])
    for t in range(1, T):
        for j in range(n):
            best, arg = -math.inf, 0
            for i in range(n):
                v = delta[t - 1][i] + math.log(max(model.trans[i][j], _FLOOR))
                if v > best:
                    best, arg = v, i
            delta[t][j] = best + log_em(j, obs[t])
            psi[t][j] = arg

    path = [0] * T
    path[T - 1] = max(range(n), key=lambda i: delta[T - 1][i])
    for t in range(T - 2, -1, -1):
        path[t] = psi[t + 1][path[t + 1]]
    return path


def baum_welch(obs: list[float], model: GaussianHMM, n_iter: int = 200,
               tol: float = 1e-10, min_sd: float = 1e-6
               ) -> tuple[GaussianHMM, float, int]:
    """Estimation par maximum de vraisemblance (Baum-Welch / EM).

    Retourne le modèle ajusté, sa log-vraisemblance et le nombre d'itérations.
    La log-vraisemblance croît à chaque pas — propriété de l'algorithme EM,
    et **piège principal de la méthode** : la convergence n'est pas une
    validation, elle est garantie même quand il n'y a rien à trouver.

    L'optimum atteint est local. Le modèle initial fait donc partie du
    résultat, et il est passé explicitement plutôt que tiré au hasard, pour
    que l'estimation soit reproductible.
    """
    n = model.n_states
    prev = -math.inf
    current = model
    for it in range(1, n_iter + 1):
        loglik, gamma, xi = forward_backward(current, obs)
        T = len(obs)

        start = [max(gamma[0][i], _FLOOR) for i in range(n)]
        s0 = sum(start)
        start = [v / s0 for v in start]

        trans = []
        for i in range(n):
            denom = sum(gamma[t][i] for t in range(T - 1)) or _FLOOR
            row = [sum(xi[t][i][j] for t in range(T - 1)) / denom for j in range(n)]
            rs = sum(row) or _FLOOR
            trans.append(tuple(v / rs for v in row))

        means, sds = [], []
        for i in range(n):
            w = sum(gamma[t][i] for t in range(T)) or _FLOOR
            mu = sum(gamma[t][i] * obs[t] for t in range(T)) / w
            var = sum(gamma[t][i] * (obs[t] - mu) ** 2 for t in range(T)) / w
            means.append(mu)
            sds.append(max(math.sqrt(max(var, 0.0)), min_sd))

        current = GaussianHMM(tuple(start), tuple(trans), tuple(means), tuple(sds))
        if abs(loglik - prev) < tol * max(1.0, abs(loglik)):
            return current, log_likelihood(current, obs), it
        prev = loglik
    return current, log_likelihood(current, obs), n_iter


# --- Ce qui rend un régime réfutable ---------------------------------------


def separability(mu_a: float, mu_b: float, sd: float) -> float:
    """Séparabilité `d′ = |µ_a − µ_b|/σ` de deux régimes à variance commune.

    C'est la distance de Mahalanobis entre les deux émissions, et la seule
    grandeur qui décide de la distinguabilité — ni la persistance des
    régimes, ni la longueur de l'historique, ni la qualité de l'optimiseur
    n'y changent quoi que ce soit.
    """
    if sd <= 0:
        raise ValueError("sd doit être > 0")
    return abs(mu_a - mu_b) / sd


def bayes_error(d_prime: float) -> float:
    """Taux d'erreur irréductible de classification : `Φ(−d′/2)`.

    Deux gaussiennes équiprobables de séparation `d′` ne peuvent pas être
    distinguées, observation par observation, mieux que cela — quel que soit
    le classifieur. À `d′ = 0,3`, typique d'un écart de rendement moyen entre
    régimes de gamma sur données journalières, l'erreur vaut 44 % : le régime
    est, à l'échelle du point, presque indécidable. Seule l'accumulation le
    rend visible, et c'est pourquoi la persistance compte.
    """
    return norm_cdf(-abs(d_prime) / 2.0)


def observations_to_separate(d_prime: float, alpha: float = 0.05,
                             power: float = 0.80) -> float:
    """Observations par régime pour détecter une séparation `d′`.

    Test bilatéral de différence de moyennes à variance commune :

        n = 2·(z_{1−α/2} + z_power)²/d′².

    La dépendance en `1/d′²` est la contrainte réelle du conditionnement de
    régime : diviser la séparation par deux multiplie par quatre l'historique
    nécessaire — et l'historique, lui, ne se multiplie pas.
    """
    if d_prime <= 0:
        return math.inf
    z_a = _norm_ppf(1.0 - alpha / 2.0)
    z_b = _norm_ppf(power)
    return 2.0 * (z_a + z_b) ** 2 / d_prime**2


def effective_separability(d_prime: float, sojourn: float) -> float:
    """Séparation effective d'un régime observé sur toute sa durée de séjour.

    Un régime qui dure `m` périodes offre `m` observations corrélées à la
    même hypothèse ; la séparation utile croît en `√m`. C'est le seul canal
    par lequel la persistance aide, et il est borné : à séjour de vingt jours
    et `d′ = 0,3`, la séparation par épisode ne vaut que 1,34 — un régime
    reste, épisode par épisode, une hypothèse faible.
    """
    if sojourn <= 0:
        raise ValueError("sojourn doit être > 0")
    return d_prime * math.sqrt(sojourn)


def aic(loglik: float, n_params: int) -> float:
    """Critère d'Akaike : `2k − 2·lnL`. Plus petit vaut mieux."""
    return 2.0 * n_params - 2.0 * loglik


def bic(loglik: float, n_params: int, n_obs: int) -> float:
    """Critère bayésien : `k·ln(n) − 2·lnL`.

    Sa pénalité croît avec la taille d'échantillon, celle de l'AIC non. Sur
    les longueurs d'historique dont dispose une stratégie intraday — quelques
    milliers de séances au mieux — le BIC écarte le troisième état que l'AIC
    retient presque toujours.
    """
    if n_obs < 1:
        raise ValueError("n_obs doit être >= 1")
    return n_params * math.log(n_obs) - 2.0 * loglik


def two_state_from_persistence(p_stay_a: float, p_stay_b: float,
                               mu_a: float, mu_b: float,
                               sd_a: float, sd_b: float) -> GaussianHMM:
    """Construit un HMM à deux états à partir de ses persistances.

    Forme d'usage la plus courante en gestion : on décrit un régime par sa
    durée moyenne et son émission, non par une matrice de transition brute.
    """
    for p in (p_stay_a, p_stay_b):
        if not 0.0 < p < 1.0:
            raise ValueError("les persistances doivent être dans ]0, 1[")
    trans = ((p_stay_a, 1.0 - p_stay_a), (1.0 - p_stay_b, p_stay_b))
    model = GaussianHMM((0.5, 0.5), trans, (mu_a, mu_b), (sd_a, sd_b))
    return GaussianHMM(model.stationary(), trans, (mu_a, mu_b), (sd_a, sd_b))
