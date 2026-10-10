"""Assemble ALP Desk en un seul fichier HTML.

python3 build.py                 -> dist/alp-desk.html  (tous les desks)
python3 build.py --only risk     -> dist/only-risk.html (socle + accueil + un desk, pour tester)
python3 build.py --out X.html    -> chemin de sortie libre
python3 build.py --fonts         -> remplace Google Fonts par les fichiers locaux (aperçu hors ligne)
"""
import os, re, sys, glob

D = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
only = args[args.index('--only') + 1] if '--only' in args else None
out = args[args.index('--out') + 1] if '--out' in args else None
fonts = '--fonts' in args

css = open(os.path.join(D, 'src', 'core.css')).read()
core = open(os.path.join(D, 'src', 'core.js')).read()
shell = open(os.path.join(D, 'src', 'shell.html')).read()

desks = []
for p in sorted(glob.glob(os.path.join(D, 'src', 'desks', '*.js'))):
    name = os.path.splitext(os.path.basename(p))[0]
    if only and name not in (only, 'home'):
        continue
    src = open(p).read()
    desks.append('/* ===== desk : %s ===== */\n(function(){\n%s\n})();' % (name, src))

js = core + '\n' + '\n'.join(desks) + '\nT.boot();\n'
logo_js = re.search(r"T\.logo = function \(size\) \{\s*return '(.*?)';", core, re.S).group(1)
logo = logo_js.replace("' + (size || 26) + '", '26')
page = shell.replace('/*CSS*/', css).replace('/*JS*/', js).replace('<!--LOGO-->', logo)
if '</script' in js.replace('</script>\n', ''):
    pass
if fonts:
    ff = ('<style>@font-face{font-family:"Geist";src:url(/plan/fonts/fontsource-variable-geist-5.3.0/files/geist-latin-wght-normal.woff2) format("woff2");font-weight:100 900}'
          '@font-face{font-family:"Geist Mono";src:url(/plan/fonts/fontsource-variable-geist-mono-5.3.0/files/geist-mono-latin-wght-normal.woff2) format("woff2");font-weight:100 900}'
          '@font-face{font-family:"Instrument Serif";font-style:italic;src:url(/desk/fonts/instrument-serif-latin-400-italic.woff2) format("woff2")}'
          '@font-face{font-family:"Instrument Serif";font-style:normal;src:url(/desk/fonts/instrument-serif-latin-400-normal.woff2) format("woff2")}</style>')
    page = re.sub(r'<link rel="stylesheet" href="https://fonts.googleapis.com[^>]*>', ff, page)
    page = '<!doctype html><html lang="fr"><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover"><style>[hidden]{display:none!important}body{margin:0}</style></head><body>' + page + '</body></html>'
target = out or os.path.join(D, 'dist', ('only-%s.html' % only) if only else 'alp-desk.html')
os.makedirs(os.path.dirname(target), exist_ok=True)
open(target, 'w').write(page)
open(target + '.js', 'w').write(js)
print('écrit', target, len(page), 'octets,', len(desks), 'desks')
