"""Gera (ou apaga, com --clean) as fixtures dos testes que não ficam no repositório.
Usado igual aqui e na CI (.github/workflows/testes.yml). Rodar de dentro de dev/:
    python3 fixtures.py          # gera rb.pdf, small.pmtiles(+part1..3), dl/ e testmap.pmtiles (make_testmap.py)
    python3 fixtures.py --clean  # apaga
small.pmtiles = roads.pmtiles + 5 MB de zeros no fim (o leitor PMTiles ignora o que vem depois dos dados),
para dar 3 partes de 2 MB no teste de instalação/download em partes."""
import hashlib, json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
PARTS = ['small.pmtiles.part1', 'small.pmtiles.part2', 'small.pmtiles.part3']

if '--clean' in sys.argv:
    for f in ['rb.pdf', 'small.pmtiles', 'testmap.pmtiles'] + PARTS:
        if os.path.exists(f):
            os.remove(f)
    shutil.rmtree('dl', ignore_errors=True)
    print('fixtures apagadas')
    sys.exit(0)

from PIL import Image  # noqa: E402  (só precisa ao gerar)

ims = [Image.new('RGB', (600, 800), c) for c in ('white', 'gray', 'yellow')]
ims[0].save('rb.pdf', save_all=True, append_images=ims[1:])

data = open('roads.pmtiles', 'rb').read() + b'\0' * 5_000_000
open('small.pmtiles', 'wb').write(data)
step = 2 * 1024 * 1024
for i, name in enumerate(PARTS):
    open(name, 'wb').write(data[i * step:(i + 1) * step])
assert sum(os.path.getsize(p) for p in PARTS) == len(data), 'as 3 partes não cobrem o arquivo'

os.makedirs('dl', exist_ok=True)
man = []
for name in PARTS:
    shutil.copy(name, os.path.join('dl', name))
    b = open(name, 'rb').read()
    man.append({'f': name, 'size': len(b), 'sha256': hashlib.sha256(b).hexdigest()})
json.dump({'id': 'teste-1', 'label': 'Teste', 'size': sum(p['size'] for p in man), 'parts': man}, open('dl/manifest.json', 'w'))
import make_testmap  # noqa: E402
make_testmap.build(os.path.join(HERE, 'testmap.pmtiles'))
print('fixtures prontas: rb.pdf, small.pmtiles (+3 partes), dl/, testmap.pmtiles')
