"""Ajusta o index.html copiado para www/: bibliotecas e fontes locais (o APK tem que abrir sem internet)
e o runtime do Capacitor. Falha em voz alta se algum trecho esperado não existir mais.
uso: python3 rewrite-html.py www/index.html"""
import sys

p = sys.argv[1]
s = open(p, encoding='utf-8').read()

def rep(old, new):
    global s
    if s.count(old) != 1:
        sys.exit(f'rewrite-html: esperava 1 ocorrência e achei {s.count(old)} de: {old[:80]}')
    s = s.replace(old, new)

import re
# a CSP é só da versão web (o Capacitor injeta o próprio código no WebView); integrity/crossorigin não valem para a cópia local
n = len(re.findall(r'<meta http-equiv="Content-Security-Policy"[^>]*>\n?', s))
if n != 1:
    sys.exit(f'rewrite-html: esperava 1 CSP e achei {n}')
s = re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]*>\n?', '', s)
rep('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css" integrity="sha512-h9FcoyWjHcOcmEVkxOfTLnmZFWIH0iZhZT1H2TbOq55xssQGEJHEaIm+PgoUaZbRvQTNTluNOEfb1ZRy6D3BOw==" crossorigin="anonymous">', '<link rel="stylesheet" href="lib/leaflet/leaflet.css">')
rep('<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js" integrity="sha512-puJW3E/qXDqYp9IfhAI54BJEaWIfloJ7JWs7OeD5i6ruC9JZL1gERT1wjtwXFlh7CjE7ZJ+/vcRZRkIYIb6p4g==" crossorigin="anonymous"></script>',
    '<script src="lib/capacitor.js"></script>\n<script src="lib/leaflet/leaflet.js"></script>')
rep('<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Inter:wght@400;600&display=swap" rel="stylesheet" crossorigin="anonymous">',
    '<link rel="stylesheet" href="fonts/orbitron-700.css"><link rel="stylesheet" href="fonts/orbitron-900.css"><link rel="stylesheet" href="fonts/inter-400.css"><link rel="stylesheet" href="fonts/inter-600.css">')
for bad in ('cdnjs.cloudflare.com', 'fonts.googleapis.com', 'fonts.gstatic.com'):
    if bad in s:
        sys.exit('rewrite-html: sobrou referência externa: ' + bad)
open(p, 'w', encoding='utf-8').write(s)
print('index.html do APK ajustado')
