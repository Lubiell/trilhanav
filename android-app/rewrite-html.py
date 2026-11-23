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

rep('https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css', 'lib/leaflet/leaflet.css')
rep('<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>',
    '<script src="lib/capacitor.js"></script>\n<script src="lib/leaflet/leaflet.js"></script>')
rep('<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Inter:wght@400;600&display=swap" rel="stylesheet" crossorigin="anonymous">',
    '<link rel="stylesheet" href="fonts/orbitron-700.css"><link rel="stylesheet" href="fonts/orbitron-900.css"><link rel="stylesheet" href="fonts/inter-400.css"><link rel="stylesheet" href="fonts/inter-600.css">')
for bad in ('cdnjs.cloudflare.com', 'fonts.googleapis.com', 'fonts.gstatic.com'):
    if bad in s:
        sys.exit('rewrite-html: sobrou referência externa: ' + bad)
open(p, 'w', encoding='utf-8').write(s)
print('index.html do APK ajustado')
