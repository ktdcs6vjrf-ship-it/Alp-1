"""Feuille de style des figures — partagée par le paper et les aperçus."""

FIGURE_CSS = """
  /* ---------- figures ---------- */

  figure svg.fig { display: block; width: 100%; height: auto; margin: 0 auto; }

  .fig text { font-family: var(--mono); font-variant-numeric: lining-nums tabular-nums; }
  .fig .tk   { font-size: 9.5px; fill: var(--muted); }
  .fig .ax   { font-size: 10.5px; fill: var(--soft); font-family: var(--serif); }
  .fig .lg   { font-size: 10px;   fill: var(--soft); font-family: var(--serif); }
  .fig .dl   { font-size: 9.5px;  fill: var(--ink); }
  .fig .cell { font-size: 10px;   font-variant-numeric: lining-nums tabular-nums; }
  .fig .halo { paint-order: stroke; stroke: var(--paper); stroke-width: 3.4px;
               stroke-linejoin: round; }

  .fig .gl   { stroke: var(--hair); stroke-width: 1; fill: none; }
  .fig .ba   { stroke: var(--hair); stroke-width: 1; }
  .fig .mark { stroke: var(--hair); stroke-width: 1; }
  .fig .zero { stroke: var(--soft); stroke-width: 1; }
  .fig .band { fill: var(--wash); }
  .fig .hl   { fill: none; stroke: var(--ink); stroke-width: 1.6; }

  .fig .ln   { fill: none; stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
  .fig .pt   { stroke: var(--paper); stroke-width: 2; }

  .fig .s1 { stroke: var(--s1); }  .fig .pt.s1 { fill: var(--s1); }
  .fig .s2 { stroke: var(--s2); }  .fig .pt.s2 { fill: var(--s2); }
  .fig .s3 { stroke: var(--s3); }  .fig .pt.s3 { fill: var(--s3); }
  /* Un quatrième trait, du côté négatif de l'échelle divergente : `negf` ne
     remplit que des aplats, et une courbe qui porte le signe d'un verdict ne
     peut pas emprunter la teinte d'une série ordinaire. */
  .fig .neg { stroke: var(--dv-neg); }  .fig .pt.neg { fill: var(--dv-neg); }

  .fig .area { stroke: var(--paper); stroke-width: 2; }
  .fig .area.ar1 { fill: var(--s1); }
  .fig .area.ar2 { fill: var(--s3); }
  .fig .area.ar3 { fill: var(--s2); }
  rect.area { stroke: none; }

  .fig .mesh  { stroke: var(--paper); stroke-width: 1; }

  /* Nuage de points d'une surface : un point est un trait de longueur nulle
     à bout rond, ce qui permet d'en grouper des centaines dans un seul
     tracé. La classe de rampe porte la teinte, l'épaisseur porte la
     hauteur. Les nœuds sont les sommets de la grille de données, et eux
     seuls portent une infobulle. */
  .fig .nuage { fill: none; stroke-linecap: round; }
  .fig .noeud { stroke: var(--paper); stroke-width: 0.8; }
  .fig .nuage.hm0 { stroke: var(--hm0); }  .fig .noeud.hm0 { fill: var(--hm0); }
  .fig .nuage.hm1 { stroke: var(--hm1); }  .fig .noeud.hm1 { fill: var(--hm1); }
  .fig .nuage.hm2 { stroke: var(--hm2); }  .fig .noeud.hm2 { fill: var(--hm2); }
  .fig .nuage.hm3 { stroke: var(--hm3); }  .fig .noeud.hm3 { fill: var(--hm3); }
  .fig .nuage.hm4 { stroke: var(--hm4); }  .fig .noeud.hm4 { fill: var(--hm4); }
  .fig .nuage.hm5 { stroke: var(--hm5); }  .fig .noeud.hm5 { fill: var(--hm5); }
  .fig .nuage.hm6 { stroke: var(--hm6); }  .fig .noeud.hm6 { fill: var(--hm6); }
  .fig .nuage.hm7 { stroke: var(--hm7); }  .fig .noeud.hm7 { fill: var(--hm7); }
  .fig .nuage.up  { stroke: var(--s1); }   .fig .noeud.up  { fill: var(--s1); }
  .fig .nuage.dn  { stroke: var(--dv-neg); } .fig .noeud.dn { fill: var(--dv-neg); }
  .fig .nuage.ze  { stroke: var(--mid); }  .fig .noeud.ze  { fill: var(--mid); }
  .fig .up    { fill: var(--s1); }
  .fig .dn    { fill: var(--dv-neg); }
  .fig .ze    { fill: var(--mid); }
  .fig .floor { fill: none; stroke: var(--hair); stroke-width: 1; }
  .fig .post  { stroke: var(--hair); stroke-width: 1; }

  /* --- chrome de panneau : figures en plusieurs cadres --- */

  .fig .hdr {
    font-family: var(--serif); font-size: 10px; font-weight: 600;
    fill: var(--ink); letter-spacing: 0.09em; text-transform: uppercase;
  }
  .fig .sub   { font-size: 9.5px; fill: var(--muted); }
  .fig .read  { font-size: 10px; fill: var(--ink); }
  .fig .frame { fill: none; stroke: var(--hair); stroke-width: 1; }
  .fig .hsep  { stroke: var(--hair); stroke-width: 1; }
  .fig .lvl   { fill: none; stroke: var(--soft); stroke-width: 1; stroke-dasharray: 4 3; }
  .fig .lvl.strong { stroke: var(--ink); stroke-dasharray: none; }
  .fig .tag   { fill: var(--paper); stroke: var(--hair); stroke-width: 1; }
  .fig .tagtx { font-size: 9px; fill: var(--ink); }
  .fig .px    { fill: none; stroke: var(--ink); stroke-width: 1.4; }
  .fig .s1f { fill: var(--s1); }  .fig .s2f { fill: var(--s2); }  .fig .s3f { fill: var(--s3); }
  .fig .negf { fill: var(--dv-neg); }
  .fig .wash  { fill: var(--wash); }
  .fig .swatch-wash { fill: var(--wash); stroke: var(--hair); stroke-width: 1; }

  .fig .hm0 { fill: var(--hm0); }  .fig .hm4 { fill: var(--hm4); }
  .fig .hm1 { fill: var(--hm1); }  .fig .hm5 { fill: var(--hm5); }
  .fig .hm2 { fill: var(--hm2); }  .fig .hm6 { fill: var(--hm6); }
  .fig .hm3 { fill: var(--hm3); }  .fig .hm7 { fill: var(--hm7); }
  .fig .cl-lo { fill: var(--ink); }
  .fig .cl-hi { fill: var(--paper); }

  /* --- rampe séquentielle en trait --------------------------------------
     Les classes `hm*` posent un remplissage. Une polyligne qui les porterait
     seule verrait ce remplissage écraser le `fill: none` de `.ln`, la règle
     venant plus loin dans la feuille à spécificité égale — et la courbe se
     refermerait en coin plein. Ces règles à deux classes tranchent, et
     redonnent le trait. */

  .fig .ln.hm0 { stroke: var(--hm0); fill: none; }
  .fig .ln.hm1 { stroke: var(--hm1); fill: none; }
  .fig .ln.hm2 { stroke: var(--hm2); fill: none; }
  .fig .ln.hm3 { stroke: var(--hm3); fill: none; }
  .fig .ln.hm4 { stroke: var(--hm4); fill: none; }
  .fig .ln.hm5 { stroke: var(--hm5); fill: none; }
  .fig .ln.hm6 { stroke: var(--hm6); fill: none; }
  .fig .ln.hm7 { stroke: var(--hm7); fill: none; }
  .fig .pt.hm3 { fill: var(--hm3); }
  .fig .pt.hm5 { fill: var(--hm5); }
  .fig .pt.hm7 { fill: var(--hm7); }
"""

# Jetons de couleur des figures. Palette catégorielle validée (séparation CVD
# et contraste vérifiés sur les deux fonds du document) ; rampe séquentielle
# bleue, inversée en thème sombre pour que « fort » reste lumineux.
FIGURE_TOKENS_LIGHT = """
    --s1: #2a78d6; --s2: #eb6834; --s3: #1baf7a;
    --dv-neg: #e34948; --mid: #f0efec;
    --hm0: #cde2fb; --hm1: #9ec5f4; --hm2: #6da7ec; --hm3: #3987e5;
    --hm4: #2a78d6; --hm5: #256abf; --hm6: #184f95; --hm7: #0d366b;
"""

FIGURE_TOKENS_DARK = """
    --s1: #3987e5; --s2: #d95926; --s3: #199e70;
    --dv-neg: #e66767; --mid: #383835;
    --hm0: #0d366b; --hm1: #184f95; --hm2: #256abf; --hm3: #2a78d6;
    --hm4: #3987e5; --hm5: #6da7ec; --hm6: #9ec5f4; --hm7: #cde2fb;
"""

# ---------------------------------------------------------------------------
# Jeu « terminal » — fond sombre engagé
# ---------------------------------------------------------------------------

# Le document nº 3 ne suit pas le thème du lecteur : il s'engage sur un fond
# sombre unique. Ce jeu lui est propre et laisse les trois autres papiers
# intacts. La rampe séquentielle est une rampe de **luminance sur une seule
# teinte** : sur fond sombre, « fort » doit être lumineux, faute de quoi la
# valeur haute disparaît dans le fond.
#
# Le bas de la rampe démarre nettement au-dessus du fond, et non près de lui.
# Une rampe qui partirait du noir rendrait invisible toute valeur basse : une
# surface dont les valeurs occupent la moitié inférieure du domaine se lirait
# alors comme une masse uniforme, ce qui est exactement le contraire de ce
# qu'une rampe séquentielle est censée montrer.

FIGURE_TOKENS_TERMINAL = """
    --s1: #9b8cff; --s2: #e4e6ea; --s3: #6e757d;
    --dv-neg: #e0625c; --mid: #22262c;
    --hm0: #3b3468; --hm1: #4a4184; --hm2: #5b50a0; --hm3: #6d60ba;
    --hm4: #8071d1; --hm5: #9585e4; --hm6: #ab9bf2; --hm7: #c6baff;
"""

# Réglages de trait propres au fond sombre. Les épaisseurs de la feuille
# commune sont calibrées pour de l'encre sur du blanc ; sur fond sombre, un
# trait clair paraît plus épais qu'il n'est, et il faut l'affiner pour
# retrouver le même poids optique.

FIGURE_CSS_TERMINAL = """
  /* ---------- fond sombre : réglages de trait ---------- */

  .fig text { font-family: var(--mono); }
  .fig .ax, .fig .lg { font-family: var(--mono); font-size: 9.5px; }
  .fig .hdr { font-family: var(--mono); letter-spacing: 0.12em; }

  .fig .gl    { stroke: var(--hair); stroke-width: 0.8; }
  .fig .ba    { stroke: var(--muted); stroke-width: 0.8; }
  .fig .floor { stroke: var(--hair); stroke-width: 0.7; }
  .fig .post  { stroke: var(--hair); stroke-width: 0.7; }
  .fig .mesh  { stroke: var(--paper); stroke-width: 0.6; }
  .fig .ln    { stroke-width: 1.4; }
  .fig .frame { stroke: var(--hair); stroke-width: 0.8; }
  .fig .hsep  { stroke: var(--hair); stroke-width: 0.8; }
  .fig .lvl   { stroke: var(--muted); stroke-width: 0.8; }
  .fig .lvl.strong { stroke: var(--soft); }
  .fig .pt    { stroke: var(--paper); stroke-width: 1.4; }

  /* Nuage de trajectoires : chaque chemin est presque invisible, et c'est
     leur superposition qui dessine la densité. */
  .fig .path-mc { fill: none; stroke: var(--s2); stroke-width: 0.5;
                  stroke-opacity: 0.055; }
  .fig .band-mc { fill: var(--s1); fill-opacity: 0.14; stroke: none; }
  .fig .quant   { fill: none; stroke: var(--ink); stroke-width: 1.2; }
  .fig .quant.dash { stroke-dasharray: 3 3; stroke: var(--soft); }
  .fig .barfill { fill: var(--s3); }
  .fig .barfill.inner { fill: var(--s2); }
"""
