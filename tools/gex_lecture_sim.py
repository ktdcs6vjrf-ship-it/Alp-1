"""Transcription Python de la boucle de lecture de pine/alp0-gex.pine.

Aucun compilateur Pine n'est joignable depuis le depot : ce fichier est la
seule facon de verifier qu'un collage rend les zones attendues sans ouvrir
TradingView. Il ne participe ni aux documents ni aux tests.
"""
MAXN, MINTICK, CLOSE, BASIS, BANDE_PCT = 20, 0.25, 29221.0, 110.47, 3.0


def nettoyer_nombre(s):
    for ch in (",", " ", "*", "`", "$", "_"):
        s = s.replace(ch, "")
    return s.strip()


def nettoyer_tag(s):
    for ch in ("*", "`", "#"):
        s = s.replace(ch, "")
    return s.replace("-", " ").strip()


def tonumber(s):
    try:
        return float(s)
    except ValueError:
        return None


def tete_numerique(s):
    t = nettoyer_tag(s)
    out = ""
    for ch in t[:3]:
        if tonumber(ch) is None:
            break
        out += ch
    return out


def code_de(tag, pref):
    """La table de correspondance du document, en un seul endroit."""
    t = tag.lower().strip()
    if t == "":
        c = ""
    elif "macro" in t or t == "rm":
        c = "RM"
    elif "flip" in t or "hvl" in t:
        c = "HVL"
    elif "max pain" in t or "maxpain" in t or t == "mp":
        c = "MP"
    elif "gamma wall" in t or "major wall" in t or t == "gw":
        c = "GW"
    elif "call" in t or "resist" in t or t == "cr":
        c = "CR"
    elif "put" in t or "support" in t or t == "ps":
        c = "PS"
    else:
        c = t.upper()
    # RM est exempt de prefixe : « macro » EST son echeance.
    deja = c != "" and tonumber(c[0]) is not None
    return c if (c == "" or pref == "" or deja or c == "RM") else pref + c


def lire(raw):
    prix, codes, n, ech = [None] * MAXN, [""] * MAXN, 0, []
    bande = CLOSE * BANDE_PCT / 100.0
    titres = "#" in raw
    section = "autre" if titres else "niveaux"
    prefixe = ""
    for row in raw.split("\n"):
        row = row.strip()
        if row.startswith("#"):
            l = row.lower()
            section = ("niveaux" if ("level" in l or "niveau" in l) else
                       "contexte" if ("context" in l or "contexte" in l)
                       else "autre")
        elif row and section != "autre":
            sep = "=" if "=" in row else ":" if ":" in row else "|" if "|" in row else ""
            parts = [row] if sep == "" else row.split(sep)
            gauche = parts[0].strip()
            droite = parts[1].strip() if len(parts) > 1 else ""
            if section == "contexte":
                if "horizon" in gauche.lower():
                    prefixe = tete_numerique(droite)
            elif n < MAXN:
                vG = tonumber(nettoyer_nombre(gauche))
                vD = tonumber(nettoyer_nombre(droite))
                v, tg = None, ""
                if vG is not None:
                    v, tg = vG, nettoyer_tag(droite)
                elif vD is not None:
                    v, tg = vD, nettoyer_tag(gauche)
                if v is not None and (abs(v - CLOSE) <= bande
                                      or abs(v + BASIS - CLOSE) <= bande):
                    cd = code_de(tg, prefixe)
                    deja = next((j for j in range(n)
                                 if abs(prix[j] - v) < MINTICK), -1)
                    if deja >= 0:
                        anc = codes[deja]
                        if cd and cd not in anc:
                            codes[deja] = cd if anc == "" else anc + "/" + cd
                    else:
                        prix[n], codes[n] = v, cd
                        ech.append(v)
                        n += 1
    med = sorted(ech)[len(ech) // 2] if ech else None
    return prix[:n], codes[:n], med


EXPORT = """# $NDX watchlist · 0 dte
## Context
- **symbol:** NDX
- **horizon:** 0 dte
- **chain snapshot:** 2026-09-14T14:45:02-04:00
- **table rows:** 22
## Levels
- **flip:** 29,280.00
- **major wall:** 29,290.00
- **call wall:** 29,250.00
- **put wall:** 29,250.00
- **max pain:** 29,175.00
## Data
```csv
expiration,settlement,call_put,strike,0dte_net,0dte_abs
2026-09-14,PM,C,29200.00,0,0
2026-09-14,PM,P,29250.00,-207160033.720062,-207160033.720062
```
"""

DEUX_ECHEANCES = EXPORT + """
## Context
- **horizon:** 30 dte
## Levels
- **call wall:** 29,600.00
- **put wall:** 28,900.00
- **resistance macro:** 29,850.00
- **R1:** 29,420.00
- **S1:** 29,050.00
"""

NUE = "29250 = 0CR\n29280 : gamma flip\n29175 | max pain\n29290"

if __name__ == "__main__":
    for nom, texte in (("export 0 dte", EXPORT),
                       ("deux echeances collees a la suite", DEUX_ECHEANCES),
                       ("liste nue", NUE)):
        p, c, med = lire(texte)
        print(f"── {nom} : {len(p)} zones")
        for v, cd in zip(p, c):
            print(f"   {cd:12s} {v:10.2f}")
        if med is not None:
            es, ea = abs(med - CLOSE), abs(med + BASIS - CLOSE)
            print(f"   echelle : ecart sans base {es:.1f} · avec {ea:.1f}"
                  f"  ->  {'base appliquee' if ea <= es else 'base NON appliquee'}")
        print()
