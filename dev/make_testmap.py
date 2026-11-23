"""Gera dev/testmap.pmtiles: mapa de teste para a busca offline e a rota longa offline (t24).

Duas cidades a ~62 km uma da outra no eixo leste-oeste (lat -20):
  Vila Alegre (lon -44.30) e Pedra Azul (lon -43.70), ligadas só pela rodovia "BR-999".
- z14: em volta de cada cidade (uns 3 km), malha de ruas com nome ("Rua das Flores", "Avenida Brasil"...), um posto (pois)
  e o começo da rodovia. Uma rua de terra ("Estrada do Sítio") sai de Vila Alegre para o norte, só em z14.
- z10, z11, z12: só a rodovia (como no mapa de verdade, onde as ruas pequenas não existem nos zooms baixos).
- places (z10 e z14): as duas cidades e o povoado "Serra Velha" no meio do caminho.
Tiles MVT (gzip) num PMTiles v3. Sem dependências: o MVT e o PMTiles são escritos aqui mesmo."""
import gzip, json, math, os, struct, sys

LAT = -20.0
TOWNS = {'Vila Alegre': -44.30, 'Pedra Azul': -43.70}
VILLAGE = ('Serra Velha', -20.0, -44.0)

# ---------- protobuf / MVT ----------
def varint(n):
    out = bytearray()
    while True:
        b = n & 0x7f; n >>= 7
        if n: out.append(b | 0x80)
        else: out.append(b); return bytes(out)
def field(f, wt, payload):
    if wt == 0: return varint((f << 3) | 0) + varint(payload)
    return varint((f << 3) | 2) + varint(len(payload)) + payload
def zz(n): return (n << 1) ^ (n >> 31)

def lonlat_to_tile(lon, lat, z, x, y, ext=4096):
    n = 2 ** z
    fx = (lon + 180) / 360 * n
    fy = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return round((fx - x) * ext), round((fy - y) * ext)

def geom(kind, parts):
    """kind 1 = pontos (parts: lista de (x,y)), 2 = linhas (parts: lista de listas de (x,y))"""
    cmds = []; cx = cy = 0
    if kind == 1:
        cmds.append((len(parts) << 3) | 1)
        for x, y in parts: cmds += [zz(x - cx), zz(y - cy)]; cx, cy = x, y
    else:
        for line in parts:
            if len(line) < 2: continue
            x, y = line[0]; cmds += [(1 << 3) | 1, zz(x - cx), zz(y - cy)]; cx, cy = x, y
            cmds.append(((len(line) - 1) << 3) | 2)
            for x, y in line[1:]: cmds += [zz(x - cx), zz(y - cy)]; cx, cy = x, y
    return b''.join(varint(c) for c in cmds)

def layer(name, feats):
    keys, vals, kidx, vidx = [], [], {}, {}
    body = field(15, 0, 2) + field(1, 2, name.encode())
    for kind, parts, props in feats:
        tags = []
        for k, v in props.items():
            if k not in kidx: kidx[k] = len(keys); keys.append(k)
            if v not in vidx: vidx[v] = len(vals); vals.append(v)
            tags += [kidx[k], vidx[v]]
        f = field(2, 2, b''.join(varint(t) for t in tags)) + field(3, 0, kind) + field(4, 2, geom(kind, parts))
        body += field(2, 2, f)
    body += b''.join(field(3, 2, k.encode()) for k in keys)
    body += b''.join(field(4, 2, field(1, 2, str(v).encode())) for v in vals)
    body += field(5, 0, 4096)
    return field(3, 2, body)

# ---------- desenho do mapa ----------
def lonlat_line(pts, z, x, y): return [lonlat_to_tile(lo, la, z, x, y) for lo, la in pts]
def inside(lo, la, z, x, y, pad=0.15):
    n = 2 ** z
    fx = (lo + 180) / 360 * n - x; fy = (1 - math.asinh(math.tan(math.radians(la))) / math.pi) / 2 * n - y
    return -pad <= fx <= 1 + pad and -pad <= fy <= 1 + pad

D = 0.006   # espaçamento da malha de ruas (~600 m)
OFF = [-1.5 * D, -0.5 * D, 0.5 * D, 1.5 * D]
def town_streets(lon0, tag):
    """malha 4x4 + "Rua Principal" no meio (lat -20), com vértice em todo cruzamento (como no OSM)"""
    out = []
    names_ns = ['Rua das Flores (' + tag + ')', 'Rua Sete', 'Avenida Brasil', 'Rua do Rosário']
    names_ew = ['Rua Tiradentes', 'Rua da Matriz', 'Rua Nova', 'Avenida Minas']
    lats = sorted(OFF[:2] + [0.0] + OFF[2:])
    for i, dx in enumerate(OFF):
        out.append(([(lon0 + dx, LAT + dy) for dy in lats], {'kind': 'minor_road', 'name': names_ns[i]}))
    for j, dy in enumerate(OFF):
        out.append(([(lon0 + dx, LAT + dy) for dx in OFF], {'kind': 'minor_road', 'name': names_ew[j]}))
    out.append(([(lon0 + dx, LAT) for dx in OFF], {'kind': 'minor_road', 'name': 'Rua Principal'}))
    return out
A, B = TOWNS['Vila Alegre'], TOWNS['Pedra Azul']
# BR-999: da ponta leste da Rua Principal de Vila Alegre à ponta oeste da de Pedra Azul, com uma curva leve (0 nas pontas)
HWY = [(A + OFF[3] + i * ((B + OFF[0]) - (A + OFF[3])) / 60, LAT + 0.004 * math.sin(i / 60 * math.pi)) for i in range(61)]
STREETS = town_streets(A, 'VA') + town_streets(B, 'PA')
STREETS.append(([(A + OFF[1], LAT + OFF[3]), (A + OFF[1], LAT + 0.02), (A + OFF[1], LAT + 0.03)], {'kind': 'path', 'kind_detail': 'track', 'name': 'Estrada do Sítio'}))
POIS = [((A + OFF[2] + 0.0004, LAT - 0.0004), {'kind': 'fuel', 'name': 'Posto Trevo'}), ((B + OFF[1], LAT + OFF[2]), {'kind': 'hospital', 'name': 'Hospital São José'})]
PLACES = [((lo, LAT), {'kind': 'locality', 'kind_detail': 'town', 'name': n, 'population': 20000}) for n, lo in TOWNS.items()] + \
         [((VILLAGE[2], VILLAGE[1]), {'kind': 'locality', 'kind_detail': 'village', 'name': VILLAGE[0], 'population': 800})]

def near_town(lo, la, km=3.5):
    return any(abs(lo - tl) * 104.6 <= km and abs(la - LAT) * 111.2 <= km for tl in TOWNS.values())

def tiles_for(z):
    n = 2 ** z; out = set()
    for lo, la in HWY + [(lo, la) for s in STREETS for lo, la in s[0]]:
        fx = (lo + 180) / 360 * n; fy = (1 - math.asinh(math.tan(math.radians(la))) / math.pi) / 2 * n
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                out.add((int(fx) + dx, int(fy) + dy))
    return out

def tile(z, x, y):
    roads, pois, places = [], [], []
    # z14 só existe perto das cidades: ali a rodovia aparece em trechos separados (um por cidade), nunca ligando as duas por cima
    runs = [HWY] if z < 14 else [[p for p in HWY if near_town(*p, km=4) and abs(p[0] - tl) < 0.2] for tl in TOWNS.values()]
    for hw in runs:
        if len(hw) >= 2 and any(inside(lo, la, z, x, y, 0.05) for lo, la in hw):
            roads.append((2, [lonlat_line(hw, z, x, y)], {'kind': 'major_road', 'kind_detail': 'trunk', 'name': 'BR-999', 'ref': 'BR-999'}))
    if z == 14:
        for pts, props in STREETS:
            if any(inside(lo, la, z, x, y, 0.05) for lo, la in pts): roads.append((2, [lonlat_line(pts, z, x, y)], props))
        for (lo, la), props in POIS:
            if inside(lo, la, z, x, y, 0): pois.append((1, [lonlat_to_tile(lo, la, z, x, y)], props))
    if z in (10, 14):
        for (lo, la), props in PLACES:
            if inside(lo, la, z, x, y, 0): places.append((1, [lonlat_to_tile(lo, la, z, x, y)], props))
    if not (roads or pois or places): return None
    data = b''
    # camadas em ordem misturada, como num tile real (earth antes de roads etc.)
    data += layer('earth', [])
    if places: data += layer('places', places)
    if roads: data += layer('roads', roads)
    if pois: data += layer('pois', pois)
    return gzip.compress(data, mtime=0)

# ---------- PMTiles v3 ----------
def rotate(n, xy, rx, ry):
    if ry == 0:
        if rx == 1: xy[0] = n - 1 - xy[0]; xy[1] = n - 1 - xy[1]
        xy[0], xy[1] = xy[1], xy[0]
def zxy_to_id(z, x, y):
    acc = ((1 << (2 * z)) - 1) // 3; xy = [x, y]; d = 0; s = 1 << (z - 1) if z else 0
    while s > 0:
        rx = 1 if xy[0] & s else 0; ry = 1 if xy[1] & s else 0
        d += s * s * ((3 * rx) ^ ry); rotate(s, xy, rx, ry); s >>= 1
    return acc + d

def build(path):
    tiles = {}
    for z in (10, 11, 12, 14):
        for x, y in tiles_for(z):
            if z == 14 and not near_town(*tile_center(z, x, y), km=5): continue
            t = tile(z, x, y)
            if t: tiles[zxy_to_id(z, x, y)] = t
    ids = sorted(tiles)
    blob = b''; ents = []
    for tid in ids:
        ents.append((tid, len(blob), len(tiles[tid]))); blob += tiles[tid]
    d = varint(len(ents))
    last = 0
    for tid, _, _ in ents: d += varint(tid - last); last = tid
    d += b''.join(varint(1) for _ in ents)
    d += b''.join(varint(l) for _, _, l in ents)
    prev = None
    for tid, off, l in ents:
        d += varint(0 if prev and off == prev[0] + prev[1] else off + 1); prev = (off, l)
    root = gzip.compress(d, mtime=0)
    meta = gzip.compress(json.dumps({'name': 'TrilhaNav teste', 'vector_layers': [{'id': 'roads'}, {'id': 'places'}, {'id': 'pois'}, {'id': 'earth'}]}).encode(), mtime=0)
    root_off = 127; meta_off = root_off + len(root); data_off = meta_off + len(meta)
    e7 = lambda v: int(round(v * 1e7))
    hdr = b'PMTiles' + bytes([3])
    hdr += struct.pack('<QQQQQQQQQQQ', root_off, len(root), meta_off, len(meta), 0, 0, data_off, len(blob), len(ids), len(ids), len(ids))
    hdr += bytes([1, 2, 2, 1, 10, 14])
    hdr += struct.pack('<iiii', e7(-44.40), e7(-20.10), e7(-43.60), e7(-19.90))
    hdr += bytes([12]) + struct.pack('<ii', e7(-44.0), e7(-20.0))
    assert len(hdr) == 127
    open(path, 'wb').write(hdr + root + meta + blob)
    return len(ids)

def tile_center(z, x, y):
    n = 2 ** z; lo = (x + 0.5) / n * 360 - 180
    la = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 0.5) / n))))
    return lo, la

if __name__ == '__main__':
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'testmap.pmtiles')
    n = build(out)
    print(f'testmap.pmtiles: {n} tiles, {os.path.getsize(out) // 1024} KB')
