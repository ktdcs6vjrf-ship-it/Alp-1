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

  .fig .area { stroke: var(--paper); stroke-width: 2; }
  .fig .area.ar1 { fill: var(--s1); }
  .fig .area.ar2 { fill: var(--s3); }
  .fig .area.ar3 { fill: var(--s2); }
  rect.area { stroke: none; }

  .fig .mesh  { stroke: var(--paper); stroke-width: 1; }
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
