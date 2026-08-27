"""Quatre instruments importés d'autres disciplines, et ce qu'ils valent.

Ce fichier est une **exploration**, pas un module du noyau : il vit hors de
`alp1/` pour ne pas entrer dans les comptes que les tests gardent. Il y entrera
si l'un des instruments est retenu, et alors seulement avec sa loi nulle
câblée, comme la règle 5 l'exige.

Le protocole est celui de `report6.table_floor` : appliquer l'instrument à une
série *sans structure*, mesurer ce qu'il y voit, puis lui donner à voir ce
qu'il est censé détecter. Un instrument qui ne sépare pas les deux ne sert à
rien, quelle que soit sa réputation dans sa discipline d'origine.

Mesures faites le 27 août 2026, 10 à 24 tirages selon le coût :

    A. Irréversibilité temporelle — thermodynamique stochastique
       plancher sans structure  130×10⁻⁶ bit  (sous les 422 exigés)
       dérive plantée           z = +0,00     aveugle, et c'est normal :
                                              ce n'est pas un détecteur de dérive
       série bilinéaire, d = 3  z = +1,7      aveugle
       série bilinéaire, d = 4  z = +19 à +64  DÉTECTE
       même série, ratio de variance : 1,00   le VR n'y voit rien
       échantillon requis       ~20 000 minutes, soit 51 séances
       → RETENU à d ≥ 4. C'est le seul des quatre qui voit une classe de
         structure que le ratio de variance ne peut pas voir, par construction :
         l'autocorrélation linéaire d'une série bilinéaire est nulle à tous les
         retards.

    B. Complexité de Lempel-Ziv — information algorithmique
       plancher sans structure  1,0342 ± 0,0077
       persistance de signe 55 %  z = −1,0    insuffisant
       persistance de signe 60 %  z = −4,5    détecte
       → ÉCARTÉ. Il faut 60 % de persistance de signe pour qu'il réagisse, un
         effet qu'aucune série d'indice intraday ne porte. L'entropie de
         permutation, déjà au dépôt, est plus sensible pour un coût voisin.

    C. Loi d'Omori — sismologie, décroissance des répliques
       plancher sans amas       p = +0,017 ± 0,033  (correctement nul)
       amas de volatilité α=0,15  z = +3,5   détecte
       amas de volatilité α=0,50  z = +14,6  détecte
       → RETENU, mais pour ce qu'il est : il mesure la persistance de la
         volatilité après un choc, donc une décision d'*exposition*, jamais une
         direction. Il dit combien de temps rester dehors, pas de quel côté
         entrer.

    D. Loi de Marchenko-Pastur — matrices aléatoires, physique nucléaire
       bord analytique          (1+√γ)², γ = N/T — aucune simulation
       120, 250, 500 séances    λ_max toujours sous le bord : aucun faux positif
       facteur commun à 2 %     invisible
       facteur commun à 3 %     DÉTECTE
       dérive plantée           invisible, et c'est correct : une dérive est une
                                moyenne, pas une corrélation
       → RETENU, et le plus solide des quatre pour une seule raison : sa loi
         nulle est en forme close. Il n'a pas de plancher de bruit à combattre.

Et une borne, qui ne se mesure pas mais se calcule — la limite de Gabor,
Δt·Δf ≥ 1/4π. Sur une fenêtre de 14 barres, un cycle de 20 minutes ne se
distingue pas d'un cycle de 18,0 à 22,6 minutes. Aucun réglage d'oscillateur
ne contourne cela : c'est une borne sur l'information disponible, pas un
défaut d'implémentation.
"""
from __future__ import annotations

import math
from alp1.dataset import synthetic_sessions
from alp1.varratio import log_returns
from alp1.mc import Rng

SEED = 20260827


def serie(n_days: int, seed: int, drift: float = 0.0) -> list[float]:
    """Les rendements-minute concaténés d'un historique sans structure."""
    out: list[float] = []
    for s in synthetic_sessions(n_days, drift_points_per_min=drift, seed=seed):
        out.extend(log_returns(s))
    return out


# --- A. Irréversibilité temporelle (thermodynamique stochastique) ----------
# Une martingale à accroissements symétriques est réversible en loi : la série
# lue à l'endroit et à l'envers a la même statistique. Une dynamique
# asymétrique — montée lente, chute brutale — ne l'est pas. Le ratio de
# variance est aveugle à cela : il ne lit que l'autocorrélation linéaire.

def _ordinaux(x: list[float], d: int = 3) -> dict[tuple, int]:
    c: dict[tuple, int] = {}
    for i in range(len(x) - d + 1):
        w = x[i:i + d]
        m = tuple(sorted(range(d), key=lambda k: w[k]))
        c[m] = c.get(m, 0) + 1
    return c


def irreversibilite(x: list[float], d: int = 3) -> float:
    """Divergence de Kullback-Leibler entre la série et son renversé, en bits.

    Zéro si la série est réversible. C'est une quantité *signée par le temps* :
    elle ne peut pas être fabriquée par une autocorrélation symétrique.
    """
    av, ar = _ordinaux(x, d), _ordinaux(list(reversed(x)), d)
    n_av = sum(av.values()) or 1
    n_ar = sum(ar.values()) or 1
    div = 0.0
    for m in set(av) | set(ar):
        p = (av.get(m, 0) + 0.5) / (n_av + 0.5 * math.factorial(d))
        q = (ar.get(m, 0) + 0.5) / (n_ar + 0.5 * math.factorial(d))
        div += p * math.log2(p / q)
    return div


# --- B. Complexité de Lempel-Ziv (information algorithmique) ---------------
# Elle compte les motifs *nouveaux* rencontrés en parcourant la série une fois.
# Contrairement à l'entropie de permutation, qui fixe l'ordre d à l'avance,
# elle attrape une répétition de n'importe quelle longueur.

def lempel_ziv(x: list[float]) -> float:
    """Complexité LZ76 normalisée. Vaut 1 sur une suite incompressible."""
    s = "".join("1" if v > 0 else "0" for v in x)
    n = len(s)
    if n < 8:
        return 1.0
    i, k, l, c, k_max = 0, 1, 1, 1, 1
    while True:
        if s[i + k - 1] == s[l + k - 1]:
            k += 1
            if l + k > n:
                c += 1
                break
        else:
            k_max = max(k, k_max)
            i += 1
            if i == l:
                c += 1
                l += k_max
                if l + 1 > n:
                    break
                i, k, k_max = 0, 1, 1
            else:
                k = 1
    return c / (n / math.log2(n))


# --- C. Loi d'Omori (sismologie) — répliques de volatilité -----------------
# Après une secousse, le taux de répliques décroît en 1/t^p. Transposé : après
# une minute de forte amplitude, la volatilité décroît-elle en loi de
# puissance, et l'exposant est-il stable ?

def omori(x: list[float], seuil_sigma: float = 3.0, horizon: int = 30) -> float:
    """Exposant p ajusté par moindres carrés sur log(volatilité) ~ −p·log(t)."""
    sd = (sum(v * v for v in x) / max(1, len(x))) ** 0.5 or 1.0
    chocs = [i for i, v in enumerate(x) if abs(v) > seuil_sigma * sd]
    chocs = [i for i in chocs if i + horizon < len(x)]
    if len(chocs) < 12:
        return float("nan")
    profil = []
    for t in range(1, horizon + 1):
        v = [x[i + t] ** 2 for i in chocs]
        profil.append(sum(v) / len(v))
    xs = [math.log(t) for t in range(1, horizon + 1)]
    ys = [math.log(v) if v > 0 else -30.0 for v in profil]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = sum((a - mx) ** 2 for a in xs) or 1.0
    return -num / den


# --- D. Marchenko-Pastur (matrices aléatoires, physique nucléaire) --------
# Le seul des quatre dont la loi nulle est en forme close. Sous absence de
# corrélation vraie, les valeurs propres d'une matrice de corrélation estimée
# sur N séries × T observations tombent dans [(1−√γ)², (1+√γ)²], γ = N/T.
# Tout ce qui dépasse le bord est de la structure, et non du bruit.

def bord_mp(n_series: int, n_obs: int) -> float:
    g = n_series / n_obs
    return (1.0 + math.sqrt(g)) ** 2


def plus_grande_valeur_propre(m: list[list[float]], iters: int = 300) -> float:
    """Méthode de la puissance : suffit pour la plus grande valeur propre."""
    n = len(m)
    v = [1.0 / math.sqrt(n)] * n
    lam = 0.0
    for _ in range(iters):
        w = [sum(m[i][j] * v[j] for j in range(n)) for i in range(n)]
        nrm = math.sqrt(sum(a * a for a in w)) or 1.0
        v = [a / nrm for a in w]
        lam = nrm
    return lam


def correlation_par_tranche(n_days: int, seed: int, n_tranches: int = 26,
                            drift: float = 0.0) -> tuple[float, float]:
    """Panneau tranche-horaire × jour, puis sa plus grande valeur propre."""
    sessions = synthetic_sessions(n_days, drift_points_per_min=drift, seed=seed)
    panneau = []
    for s in sessions:
        r = log_returns(s)
        larg = len(r) // n_tranches
        if larg == 0:
            continue
        panneau.append([sum(r[k * larg:(k + 1) * larg]) for k in range(n_tranches)])
    T = len(panneau)
    moy = [sum(c[k] for c in panneau) / T for k in range(n_tranches)]
    sd = [(sum((c[k] - moy[k]) ** 2 for c in panneau) / T) ** 0.5 or 1e-12
          for k in range(n_tranches)]
    corr = [[sum((c[i] - moy[i]) * (c[j] - moy[j]) for c in panneau)
             / (T * sd[i] * sd[j]) for j in range(n_tranches)]
            for i in range(n_tranches)]
    return plus_grande_valeur_propre(corr), bord_mp(n_tranches, T)


# --- Série asymétrique : montée lente, chute brutale -----------------------
# C'est la dynamique que l'irréversibilité est censée voir, et qu'aucun ratio
# de variance ne peut voir : l'autocorrélation linéaire y est nulle.

def serie_asymetrique(n: int, seed: int, part: float = 0.5) -> list[float]:
    """Marche dont une fraction `part` des pas suit un motif asymétrique.

    Le motif est neutre en moyenne — quelques petites hausses puis une baisse
    qui les annule exactement — donc invisible à toute mesure de dérive, et
    invisible au ratio de variance dont l'autocorrélation reste nulle.
    """
    g = Rng(seed)
    out: list[float] = []
    while len(out) < n:
        if g.uniform() < part:
            h = abs(g.gauss()) * 0.5
            out.extend([h, h, h, -3.0 * h])
        else:
            out.append(g.gauss())
    return out[:n]
