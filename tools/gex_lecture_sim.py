# Transcription fidele de la boucle de lecture de pine/alp0-gex.pine.
MAXN, MINTICK, CLOSE, BASIS, BANDE_PCT = 12, 0.25, 29221.0, 110.47, 1.0

def nettoyer_nombre(s):
    for ch in [",", " ", "*", "`", "$", "_"]:
        s = s.replace(ch, "")
    return s.strip()

def nettoyer_tag(s):
    for ch in ["*", "`", "#"]:
        s = s.replace(ch, "")
    return s.replace("-", " ").strip()

def tonumber(s):
    try:
        return float(s)
    except ValueError:
        return None

def famille(tag):
    t = tag.lower()
    if any(w in t for w in ("call", "resist", "cw", "cr")):
        return 0
    if any(w in t for w in ("put", "support", "pw", "ps")):
        return 1
    return 2

def lire(raw):
    lvl_idx, lvl_tag, lvl_fam, n = [None]*MAXN, [""]*MAXN, [2]*MAXN, 0
    ech, bande = [], CLOSE * BANDE_PCT / 100.0
    lisible = not ("#" in raw)
    for row in raw.split("\n"):
        row = row.strip()
        if row.startswith("#"):
            lisible = ("level" in row.lower()) or ("niveau" in row.lower())
        elif lisible and len(row) > 0 and n < MAXN:
            sep = "=" if "=" in row else ":" if ":" in row else "|" if "|" in row else ""
            parts = [row] if sep == "" else row.split(sep)
            gauche = parts[0].strip()
            droite = parts[1].strip() if len(parts) > 1 else ""
            vG, vD = tonumber(nettoyer_nombre(gauche)), tonumber(nettoyer_nombre(droite))
            v, tg = None, ""
            if vG is not None:
                v, tg = vG, nettoyer_tag(droite)
            elif vD is not None:
                v, tg = vD, nettoyer_tag(gauche)
            if v is not None:
                if abs(v - CLOSE) <= bande or abs(v + BASIS - CLOSE) <= bande:
                    deja = next((j for j in range(n) if abs(lvl_idx[j] - v) < MINTICK), -1)
                    if deja >= 0:
                        anc = lvl_tag[deja]
                        if tg and tg.lower() not in anc.lower():
                            lvl_tag[deja] = tg if anc == "" else anc + " · " + tg
                            if famille(tg) != lvl_fam[deja]:
                                lvl_fam[deja] = 2
                    else:
                        lvl_idx[n], lvl_tag[n], lvl_fam[n] = v, tg, famille(tg)
                        ech.append(v); n += 1
    med = sorted(ech)[len(ech)//2] if ech else None
    return lvl_idx[:n], lvl_tag[:n], lvl_fam[:n], med

EXPORT = """# $NDX watchlist · 0 dte
Machine-readable export of one gexbot watchlist broadcast.
## Context
- **symbol:** NDX
- **horizon:** 0 dte
- **charts:** `0dte_net` (GEX_OI), `0dte_abs` (GEX_OI)
- **chain snapshot:** 2026-09-14T14:45:02-04:00
- **posted at:** 2026-09-14T15:00:00-04:00
- **table rows:** 22
## Levels
- **flip:** 29,280.00
- **major wall:** 29,290.00
- **call wall:** 29,250.00
- **put wall:** 29,250.00
- **max pain:** 29,175.00
## Columns
- `expiration` — expiration
- `strike` — strike (price)
## Data
```csv
expiration,settlement,call_put,strike,0dte_net,0dte_abs
2026-09-14,PM,C,29200.00,0,0
2026-09-14,PM,P,29250.00,-207160033.720062,-207160033.720062
```
"""

NUE = "29250 = call wall\n29280 : gamma flip\n29175 | max pain\n29290"

NOMS = {0: "call", 1: "put", 2: "neutre"}
for nom, texte in (("export markdown entier", EXPORT), ("liste nue", NUE)):
    idx, tags, fams, med = lire(texte)
    print(f"── {nom} : {len(idx)} niveaux lus, mediane {med}")
    for v, t, f in zip(idx, tags, fams):
        print(f"   {v:10.2f}  {NOMS[f]:7s}  {t}")
    if med is not None:
        es, ea = abs(med - CLOSE), abs(med + BASIS - CLOSE)
        print(f"   echelle : ecart sans base {es:.1f} · avec base {ea:.1f}"
              f"  ->  {'base appliquee' if ea <= es else 'base NON appliquee'}")
    print()
