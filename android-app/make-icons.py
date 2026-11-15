"""Gera os ícones do app Android (mipmaps) a partir do desenho do icon.svg, só com Pillow.
uso: python3 make-icons.py <pasta res do android>"""
import sys, os
from PIL import Image, ImageDraw

res = sys.argv[1]
BG = (13, 22, 32, 255)

def draw(size, with_bg, round_mask=False, scale=1.0):
    S = size * 4                                   # supersampling
    im = Image.new('RGBA', (S, S), BG if with_bg else (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = S / 512 * scale; o = S * (1 - scale) / 2   # escala em torno do centro
    X = lambda v: o + v * k
    d.ellipse([X(256 - 170), X(256 - 170), X(256 + 170), X(256 + 170)], outline=(30, 155, 224, 255), width=max(1, round(22 * k)))
    d.polygon([(X(256), X(110)), (X(340), X(360)), (X(256), X(310)), (X(172), X(360))], fill=(240, 160, 32, 255))
    im = im.resize((size, size), Image.LANCZOS)
    if round_mask:
        m = Image.new('L', (size, size), 0); ImageDraw.Draw(m).ellipse([0, 0, size - 1, size - 1], fill=255)
        out = Image.new('RGBA', (size, size), (0, 0, 0, 0)); out.paste(im, (0, 0), m); im = out
    return im

for dens, px in (('mdpi', 48), ('hdpi', 72), ('xhdpi', 96), ('xxhdpi', 144), ('xxxhdpi', 192)):
    d = os.path.join(res, 'mipmap-' + dens); os.makedirs(d, exist_ok=True)
    draw(px, True).save(os.path.join(d, 'ic_launcher.png'))
    draw(px, True, round_mask=True).save(os.path.join(d, 'ic_launcher_round.png'))
    fg = round(px * 108 / 48)                      # camada de frente do ícone adaptativo: 108 dp
    draw(fg, False, scale=0.62).save(os.path.join(d, 'ic_launcher_foreground.png'))
print('ícones gerados em', res)
