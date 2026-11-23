"""Gera os ícones do app Android (mipmaps) a partir do desenho do icon.svg, só com Pillow.
uso: python3 make-icons.py <pasta res do android>   |   python3 make-icons.py --pwa <pasta do site>"""
import sys, os
from PIL import Image, ImageDraw

res = sys.argv[1]
BG = (13, 22, 32, 255)

def bez(p0, p1, p2, p3, n=60):
    return [tuple((1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t * t * c + t ** 3 * d for a, b, c, d in zip(p0, p1, p2, p3)) for t in (i / n for i in range(n + 1))]

# a trilha do icon.svg: M150 470 C150 360 362 330 330 230 S200 110 250 40 (o "S" reflete o controle anterior: 298,130)
TRAIL = bez((150, 470), (150, 360), (362, 330), (330, 230)) + bez((330, 230), (298, 130), (200, 110), (250, 40))[1:]

def draw(size, with_bg, round_mask=False, scale=1.0):
    S = size * 4                                   # supersampling
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = S / 512 * scale; o = S * (1 - scale) / 2   # escala em torno do centro
    X = lambda v: o + v * k
    if with_bg:                                    # fundo em degradê azul-escuro, cantos arredondados
        grad = Image.new('RGBA', (S, S))
        for y in range(S):
            t = y / S; grad.putpixel((0, y), (round(22 + (11 - 22) * t), round(50 + (19 - 50) * t), round(74 + (28 - 74) * t), 255))
        grad = grad.crop((0, 0, 1, S)).resize((S, S))
        m = Image.new('L', (S, S), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, S - 1, S - 1], radius=round(S * 104 / 512), fill=255)
        im.paste(grad, (0, 0), m)
    pts = [(X(x), X(y)) for x, y in TRAIL]
    w = max(1, round(56 * k))
    # trilha laranja: círculos encostados ao longo da curva (a linha grossa do Pillow deixa emendas visíveis)
    for a, b in zip(pts, pts[1:]):
        n = max(1, int(((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5 / 2))
        for i in range(n + 1):
            x, y = a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n
            d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=(240, 160, 32, 255))
    # faixa branca tracejada no meio da trilha (traço 24, espaço 22, como no SVG)
    acc, on, seg = 0.0, True, [pts[0]]
    for a, b in zip(pts, pts[1:]):
        L = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
        acc += L / k; seg.append(b)
        if acc >= (24 if on else 22):
            if on: d.line(seg, fill=(255, 255, 255, 255), width=max(1, round(9 * k)), joint='curve')
            on, acc, seg = not on, 0.0, [b]
    arrow = [(X(402), X(64)), (X(466), X(216)), (X(402), X(182)), (X(338), X(216))]
    d.polygon(arrow, fill=(30, 155, 224, 255))
    d.line(arrow + [arrow[0]], fill=(255, 255, 255, 255), width=max(1, round(12 * k)), joint='curve')
    im = im.resize((size, size), Image.LANCZOS)
    if round_mask:
        m = Image.new('L', (size, size), 0); ImageDraw.Draw(m).ellipse([0, 0, size - 1, size - 1], fill=255)
        out = Image.new('RGBA', (size, size), (0, 0, 0, 0)); out.paste(im, (0, 0), m); im = out
    return im

if res == '--pwa':                                  # ícones do site (PWA): icon-192.png e icon-512.png na pasta dada
    for px in (192, 512):
        draw(px, True).save(os.path.join(sys.argv[2], 'icon-%d.png' % px))
    print('ícones do PWA gerados'); sys.exit(0)

for dens, px in (('mdpi', 48), ('hdpi', 72), ('xhdpi', 96), ('xxhdpi', 144), ('xxxhdpi', 192)):
    d = os.path.join(res, 'mipmap-' + dens); os.makedirs(d, exist_ok=True)
    draw(px, True).save(os.path.join(d, 'ic_launcher.png'))
    draw(px, True, round_mask=True).save(os.path.join(d, 'ic_launcher_round.png'))
    fg = round(px * 108 / 48)                      # camada de frente do ícone adaptativo: 108 dp
    draw(fg, False, scale=0.62).save(os.path.join(d, 'ic_launcher_foreground.png'))
print('ícones gerados em', res)
