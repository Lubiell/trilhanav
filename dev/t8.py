"""Etapa 4: leitura de OpenRally e roadbook automático a partir de um GPX comum."""
import asyncio, sys, math, re
from playwright.async_api import async_playwright

FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

M_LAT = 111194.9
M_LON = M_LAT * math.cos(math.radians(20))
K = 1000 / M_LON  # graus de longitude por km em lat -20

# ---------- fixture OpenRally (escrito aqui, seguindo o XSD v1.0.3) ----------
NS = 'http://www.openrally.org/xmlschemas/GpxExtensions/v1.0.3'
def orwpt(km, ext, lat=-20):
    return f'<wpt lat="{lat}" lon="{-44 + km * K:.6f}"><extensions>{ext}</extensions></wpt>'
TULIP = '<![CDATA[<svg width="100" height="100"><circle cx="50" cy="50" r="30" fill="red" onload="window.__pwn=1"/><script>window.__pwn=2</script></svg>]]>'
OR_GPX = ('<?xml version="1.0"?><gpx xmlns="http://www.topografix.com/GPX/1/1" xmlns:openrally="%s" version="1.1" creator="teste">' % NS
  + '<metadata><extensions><openrally:units>metric</openrally:units><openrally:distance>10</openrally:distance></extensions></metadata>'
  + orwpt(0, '<openrally:distance>0</openrally:distance><openrally:dss name="S1"/>')
  + orwpt(1.0, '<openrally:distance>1.02</openrally:distance><openrally:danger>3</openrally:danger><openrally:wps open="800" clear="90" name="1"/>')
  + orwpt(2.0, '<openrally:distance>2.04</openrally:distance><openrally:dz/><openrally:speed>40</openrally:speed>')
  + orwpt(3.0, '<openrally:distance>3.06</openrally:distance><openrally:fz/>')
  + orwpt(4.0, '<openrally:distance>4.08</openrally:distance><openrally:stop>3</openrally:stop>')
  + orwpt(5.0, '<openrally:distance>5.1</openrally:distance><openrally:reset/><openrally:cap>90</openrally:cap>')
  + orwpt(6.0, '<openrally:distance>6.12</openrally:distance><openrally:tulip>%s</openrally:tulip>' % TULIP)
  + orwpt(7.0, '<openrally:distance>7.14</openrally:distance><openrally:neutralization>900</openrally:neutralization><openrally:fuel/>')
  + '<wpt lat="-20" lon="%.6f"><name>&lt;img src=x onerror=window.__pwn=3&gt;</name><extensions><openrally:distance>8.16</openrally:distance><openrally:wpe open="500" clear="50" name="2"/></extensions></wpt>' % (-44 + 8 * K)
  + '<trk><trkseg>' + ''.join(f'<trkpt lat="-20" lon="{-44 + i * 0.1 * K:.6f}"/>' for i in range(101)) + '</trkseg></trk></gpx>')

STATUTE = ('<?xml version="1.0"?><gpx xmlns="http://www.topografix.com/GPX/1/1" xmlns:o="%s" version="1.1" creator="t">' % NS
  + '<metadata><extensions><o:units>statute</o:units></extensions></metadata>'
  + orwpt(1.609, '<o:distance>1.0</o:distance><o:wps open="500" clear="100" name="A"/>')
  + orwpt(3.0, '<o:distance>1.86</o:distance><o:dz>25</o:dz>')
  + '<trk><trkseg>' + ''.join(f'<trkpt lat="-20" lon="{-44 + i * 0.1 * K:.6f}"/>' for i in range(61)) + '</trkseg></trk></gpx>')

# ---------- trilha sintética com curvas conhecidas ----------
def make_path(segs, step=12, jitter=0.0):
    x = y = 0.0; hdg = 90.0; pts = [(0.0, 0.0)]; dist = 0.0; marks = []
    for sg in segs:
        if sg[0] == 'L':
            n = max(1, int(sg[1] / step)); L = sg[1] / n
            for _ in range(n):
                x += L * math.sin(math.radians(hdg)); y += L * math.cos(math.radians(hdg)); dist += L; pts.append((x, y))
        else:
            _, r, ang = sg; length = r * math.radians(abs(ang)); n = max(2, int(length / step)); L = length / n; da = ang / n
            start = dist; mid = None
            for k in range(n):
                hdg += da / 2; x += L * math.sin(math.radians(hdg)); y += L * math.cos(math.radians(hdg)); hdg += da / 2; dist += L; pts.append((x, y))
                if k == n // 2: mid = (x, y)
            marks.append((start + length / 2, ang, mid[0], mid[1]))
    seed = 12345
    out = []
    for (px, py) in pts:
        seed = (seed * 1103515245 + 12345) & 0x7fffffff; jx = ((seed % 2001) / 1000 - 1) * jitter
        seed = (seed * 1103515245 + 12345) & 0x7fffffff; jy = ((seed % 2001) / 1000 - 1) * jitter
        out.append((px + jx, py + jy))
    return out, marks, dist

def to_gpx(pts, wpts=''):
    tp = ''.join(f'<trkpt lat="{-20 + py / M_LAT:.7f}" lon="{-44 + px / M_LON:.7f}"/>' for px, py in pts)
    return '<?xml version="1.0"?><gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">' + wpts + '<trk><trkseg>' + tp + '</trkseg></trk></gpx>'

SEGS = [('L', 1000), ('A', 40, 90), ('L', 1000), ('A', 40, -90), ('L', 1000), ('A', 300, 30), ('L', 800), ('A', 30, 170), ('L', 1000)]

DRIVE = '''([a,b,v,t0,lat])=>{const K=%r,step=v/3.6,out=[];let d=a*1000,t=t0;
  while(d<=b*1000){TN.onPos({timestamp:t,coords:{latitude:lat,longitude:-44+d/1000*K,altitude:0,accuracy:5,speed:v/3.6,heading:90}});
    out.push({km:+(d/1000).toFixed(3),cur:document.querySelector('#rbList .cur')?+document.querySelector('#rbList .cur').dataset.i:-1,head:document.querySelector('#rbHead').innerText});d+=step;t+=1000}
  return out}''' % K

STUB = "window.__spk=[];Object.defineProperty(window,'speechSynthesis',{value:{speak:u=>window.__spk.push(u.text),cancel(){},getVoices(){return []}},configurable:true});"

async def newpage(b):
    ctx = await b.new_context(viewport={'width': 1600, 'height': 720})
    await ctx.add_init_script(STUB)
    pg = await ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
    await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(1200)
    return pg, errs

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')

        # ================= OpenRally =================
        pg, errs = await newpage(b)
        await pg.evaluate('(x)=>TN.loadGPX(x,"or.gpx")', OR_GPX); await pg.wait_for_timeout(500)
        info = await pg.evaluate('''()=>({or:!!TN.orInfo,notes:TN.rbNotes.length,wps:TN.wps.map(w=>w.name),km:TN.rbNotes.map(n=>n.km),tkm:TN.rbNotes.map(n=>+n.tkm.toFixed(3)),
          zones:TN.zones.map(z=>[z.limit,+z.from.toFixed(2),+z.to.toFixed(2),z.src]),rows:document.querySelectorAll('#rbList .rbn').length,auto:document.querySelector('#rbAuto').classList.contains('on'),
          wp0:{clear:TN.wps[1].clear,open:TN.wps[1].open}})''')
        check('arquivo reconhecido como OpenRally com 9 notas', info['or'] and info['notes'] == 9, str({k: info[k] for k in ('or', 'notes')}))
        check('só entradas com marcador WP/DSS viram waypoints de validação', info['wps'][:2] == ['Largada do setor S1', 'WPS 1'] and len(info['wps']) == 3, str(info['wps']))
        check('km oficial do roadbook é guardado; km do trilho é separado', abs(info['km'][1] - 1.02) < 1e-6 and abs(info['tkm'][1] - 1.0) < 0.02, str((info['km'][1], info['tkm'][1])))
        check('zona de velocidade do OpenRally (dz/speed ... fz)', info['zones'] == [[40, 2.0, 3.0, 'rb']], str(info['zones']))
        check('raios open/clear do waypoint', info['wp0'] == {'clear': 90, 'open': 800}, str(info['wp0']))
        check('lista de notas desenhada e visível', info['rows'] == 9 and info['auto'], str((info['rows'], info['auto'])))
        check('nenhum script do arquivo executou (XSS em nome e SVG)', await pg.evaluate('window.__pwn===undefined'))
        tu = await pg.evaluate("[...document.querySelectorAll('#rbList img.tu')].map(i=>i.getAttribute('src').slice(0,30))")
        check('tulip em SVG vai como imagem data: (sem HTML inline)', len(tu) == 1 and tu[0].startswith('data:image/svg+xml'), str(tu))
        await pg.click('#bWp'); await pg.wait_for_timeout(300)
        nm = await pg.evaluate("document.querySelector('#wpList').innerText")
        check('nome com HTML aparece como texto na lista de waypoints', '<img src=x' in nm and await pg.evaluate('window.__pwn===undefined'), nm.replace('\n', ' | ')[:80])
        await pg.evaluate("document.querySelector('#dlgWp').close()")
        # --- dirigindo a 60 km/h ---
        t0 = 1_000_000_000_000
        steps = await pg.evaluate(DRIVE, [0.0, 8.5, 60, t0, -20])
        spk = await pg.evaluate('TN.spoken')
        check('copiloto: WP com raio "open" (800 m) fala cap', any(re.fullmatch(r'Em (750|800) metros, WPS 1\. Perigo nível 3, cap \d+ graus', x) or re.fullmatch(r'Em (750|800) metros, WPS 1, cap \d+ graus', x) for x in spk), str(spk[:6]))
        check('copiloto: parada obrigatória e abastecimento', 'Parada obrigatória de 3 segundos' in ' '.join(spk) and 'Neutralização de 15 minutos. Abastecimento' in ' '.join(spk), str(spk))
        check('copiloto: zona de velocidade do roadbook', any('zona de velocidade, limite 40' in x for x in spk), str(spk))
        cur = [s['cur'] for s in steps]
        check('nota atual só avança, do 0 ao 8', cur == sorted(cur) and cur[0] == 0 and cur[-1] == 8, str(sorted(set(cur))))
        mid = next(s for s in steps if 4.2 <= s['km'] <= 4.3)
        check('cabeçalho mostra a próxima nota, distância e CAP', 'm' in mid['head'] and 'CAP' in mid['head'], mid['head'].replace('\n', ' '))
        await pg.wait_for_timeout(1200)
        scroll = await pg.evaluate("document.querySelector('#rbAuto').scrollTop")
        check('o roadbook rolou sozinho', scroll > 100, str(scroll))
        await pg.screenshot(path='rb_or.png')
        check('sem erros (OpenRally)', not errs, str(errs))
        # --- parcial zerado pelo roadbook ---
        await pg.evaluate('()=>{TN.st.partial=7}')
        await pg.evaluate(DRIVE, [4.0, 5.2, 60, t0 + 900000, -20])
        check('"reset" do roadbook zera o parcial', await pg.evaluate('TN.st.partial') < 1, str(await pg.evaluate('TN.st.partial')))
        # --- odômetro usa o km OFICIAL ---
        await pg.evaluate('()=>{TN.st.total=0.98;TN.cfg.snap=true}')
        r = await pg.evaluate('()=>{TN.onWpValidated(1);return TN.st.total}')
        check('correção do odômetro usa o km oficial do roadbook (1.02)', abs(r - 1.02) < 1e-6, str(r))
        await pg.context.close()

        # ---- unidades statute ----
        pg, errs = await newpage(b)
        await pg.evaluate('(x)=>TN.loadGPX(x,"st.gpx")', STATUTE); await pg.wait_for_timeout(300)
        u = await pg.evaluate('()=>({km:TN.rbNotes[0].km,clear:TN.wps[0].clear,open:TN.wps[0].open,z:TN.zones.map(z=>z.limit)})')
        check('statute: milhas -> km, jardas -> m, mph -> km/h', abs(u['km'] - 1.609344) < 1e-4 and abs(u['clear'] - 91.44) < 0.01 and abs(u['open'] - 457.2) < 0.01 and u['z'] == [40], str(u))
        await pg.context.close()

        # ================= roadbook automático =================
        pts, marks, total = make_path(SEGS, jitter=3.0)
        pg, errs = await newpage(b)
        await pg.evaluate('(x)=>TN.loadGPX(x,"auto.gpx")', to_gpx(pts)); await pg.wait_for_timeout(500)
        notes = await pg.evaluate("TN.rbNotes.map(n=>({t:n.type,name:n.name,km:n.km,lat:n.lat,lon:n.lon,A:n.A||0,say:n.say||null,tulip:!!n.tulip}))")
        turns = [n for n in notes if n['t'] == 'turn']
        await pg.screenshot(path='rb_auto.png')
        check('começa em "Largada" e termina em "Chegada"', notes[0]['name'] == 'Largada' and notes[-1]['name'] == 'Chegada', str([n['name'] for n in notes]))
        check('4 curvas detectadas, nenhuma nota falsa nas retas (com ruído de 3 m)', len(turns) == 4, str([(n['name'], round(n['km'], 2), round(n['A'])) for n in turns]))
        exp = [('Curva à direita', 90), ('Curva à esquerda', -90), ('Curva leve à direita', 30), ('Retorno à direita', 170)]
        for t, e, m in zip(turns, exp, marks):
            dx = (t['lon'] + 44) * M_LON - m[2]; dy = (t['lat'] + 20) * M_LAT - m[3]; off = math.hypot(dx, dy)
            check(f'{e[0]}: texto, ângulo (±12°) e posição (±60 m do meio da curva)', t['name'] == e[0] and abs(t['A'] - e[1]) <= 12 and off <= 60, f"{t['name']} A={t['A']:.0f} a {off:.0f} m do ponto esperado")
        check('cada curva tem tulipa gerada', all(t['tulip'] for t in turns))
        await pg.evaluate('()=>{TN.cfg.noteMin=45;TN.rebuildZones()}')
        evs = await pg.evaluate('TN.events.map(e=>e.say)')
        check('copiloto: curva leve (30°) fica fora, as outras entram', sorted(evs) == sorted(['curva à direita', 'curva à esquerda', 'retorno à direita']), str(evs))
        await pg.evaluate("document.querySelector('#bSet').click()")
        await pg.evaluate('()=>{const i=document.querySelector("#sNoteMin");i.value=20;i.dispatchEvent(new Event("change"))}')
        check('mudar o mínimo do copiloto reconstrói os eventos', await pg.evaluate('TN.events.length') == 4)
        await pg.evaluate("document.querySelector('#dlgSet').close()")
        # reta pura: só largada e chegada
        pg2pts, _, _ = make_path([('L', 3000)], jitter=3.0)
        await pg.evaluate('(x)=>TN.loadGPX(x,"reta.gpx")', to_gpx(pg2pts)); await pg.wait_for_timeout(300)
        check('reta com ruído: só Largada e Chegada', await pg.evaluate('TN.rbNotes.map(n=>n.name)') == ['Largada', 'Chegada'])
        # curvas + waypoints do GPX misturados
        await pg.evaluate('(x)=>TN.loadGPX(x,"mix.gpx")', to_gpx(pts, '<wpt lat="%.7f" lon="%.7f"><name>Ponte</name></wpt>' % (-20, -44 + 500 / M_LON)))
        await pg.wait_for_timeout(300)
        names = await pg.evaluate('TN.rbNotes.map(n=>n.name)')
        check('waypoint do GPX entra na lista, na ordem do trilho', names[1] == 'Ponte' and names[2].startswith('Curva'), str(names[:4]))
        check('sem erros (automático)', not errs, str(errs))
        await pg.context.close()

        # ================= PDF + notas =================
        pg, errs = await newpage(b)
        await pg.evaluate('(x)=>TN.loadGPX(x,"auto.gpx")', to_gpx(pts)); await pg.wait_for_timeout(300)
        check('sem PDF, a lista automática aparece sozinha', await pg.evaluate("document.querySelector('#rbAuto').classList.contains('on')&&document.querySelector('#rbSwitch').style.display!=='block'"))
        await pg.set_input_files('#fileIn', 'rb.pdf'); await pg.wait_for_timeout(2500)
        st = await pg.evaluate("({pdf:getComputedStyle(document.querySelector('#rb')).display,auto:document.querySelector('#rbAuto').classList.contains('on'),sw:document.querySelector('#rbSwitch').style.display})")
        check('abrir PDF mostra o PDF e o botão de troca', st['pdf'] != 'none' and not st['auto'] and st['sw'] == 'block', str(st))
        await pg.click('#rbSwitch'); await pg.wait_for_timeout(200)
        check('botão volta para as notas', await pg.evaluate("document.querySelector('#rbAuto').classList.contains('on')"))
        await pg.set_viewport_size({'width': 1600, 'height': 360}); await pg.wait_for_timeout(300)
        await pg.keyboard.press('ArrowDown'); await pg.wait_for_timeout(900)
        check('teclas de rolagem valem para a lista de notas', await pg.evaluate("document.querySelector('#rbAuto').scrollTop") > 0)
        # nome malicioso na lista de waypoints
        await pg.evaluate('(x)=>TN.loadGPX(x,"xss.gpx")', '<?xml version="1.0"?><gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1"><wpt lat="-20" lon="-44"><name>&lt;img src=x onerror=window.__pwn=9&gt;</name></wpt><trk><trkseg><trkpt lat="-20" lon="-44"/><trkpt lat="-20" lon="-43.9"/></trkseg></trk></gpx>')
        await pg.click('#bWp'); await pg.wait_for_timeout(400)
        check('nome malicioso na lista de waypoints não executa', await pg.evaluate('window.__pwn===undefined') and '<img src=x' in await pg.evaluate("document.querySelector('#wpList').innerText"))
        check('sem erros (PDF + notas)', not errs, str(errs))
        await b.close()
    print('\nRESULTADO:', 'FALHOU ' + str(FAILS) if FAILS else 'tudo certo')
    sys.exit(1 if FAILS else 0)
asyncio.run(main())
