import sys
src = open('mandat-nq-s38d.html', encoding='utf-8').read()
F = 'fonts/fontsource-source-serif-4-5.3.0/files/source-serif-4-latin-%s-%s.woff2'
M = 'fonts/fontsource-ibm-plex-mono-5.3.0/files/ibm-plex-mono-latin-%s-normal.woff2'
faces = []
for w in (400, 500, 600, 700):
    faces.append("@font-face{font-family:'Source Serif 4';font-style:normal;font-weight:%d;src:url('%s') format('woff2');font-display:block}" % (w, F % (w, 'normal')))
for w in (400, 600):
    faces.append("@font-face{font-family:'Source Serif 4';font-style:italic;font-weight:%d;src:url('%s') format('woff2');font-display:block}" % (w, F % (w, 'italic')))
for w in (400, 500, 600, 700):
    faces.append("@font-face{font-family:'IBM Plex Mono';font-style:normal;font-weight:%d;src:url('%s') format('woff2');font-display:block}" % (w, M % w))
# on retire l appel reseau, qui ne repond pas ici, et on pose les memes fontes en local
import re
src = re.sub(r'<link rel="(?:preconnect|stylesheet)"[^>]*fonts\.(?:googleapis|gstatic)\.com[^>]*>', '', src)
src = src.replace('<style>', '<style>\n' + '\n'.join(faces) + '\n', 1)
open('preview_s38.html', 'w', encoding='utf-8').write(src)
print('preview avec les fontes reelles')
