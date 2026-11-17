"""v2.5: barra Principais + Mais, repetições removidas, postos de combustível, limite de velocidade da via e inclinação.
Overpass (postos e limites) e Valhalla simulados com page.route; sensores com DeviceMotionEvent sintético."""
import asyncio, json, math, sys
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html'
FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

STUB = "window.__spk=[];Object.defineProperty(window,'speechSynthesis',{value:{speak:u=>window.__spk.push(u.text),cancel(){},getVoices(){return []}},configurable:true});window.SpeechSynthesisUtterance=function(t){this.text=t};localStorage.setItem('tn_netOk','true');"
LAT0, LON0 = -19.9200, -43.9400
KLON = 1 / (111194.9 * math.cos(math.radians(LAT0))); KLAT = 1 / 111194.9
CORS = {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'content-type', 'Access-Control-Allow-Methods': 'POST, GET'}
calls = {'fuel': 0, 'lim': 0, 'radar': 0, 'valhalla': []}

def enc6(pts):
    out, pl, po = [], 0, 0
    for la, lo in pts:
        a, b = round(la * 1e6), round(lo * 1e6)
        for v in (a - pl, b - po):
            v = ~(v << 1) if v < 0 else v << 1
            while v >= 0x20: out.append(chr((0x20 | (v & 0x1f)) + 63)); v >>= 5
            out.append(chr(v + 63))
        pl, po = a, b
    return ''.join(out)

FUEL = [{'type': 'node', 'id': 1, 'lat': LAT0 + 3000 * KLAT, 'lon': LON0, 'tags': {'amenity': 'fuel', 'name': 'Posto Longe', 'brand': 'Ipiranga'}},
        {'type': 'way', 'id': 2, 'center': {'lat': LAT0, 'lon': LON0 + 800 * KLON}, 'tags': {'amenity': 'fuel', 'name': 'Posto <b>Perto</b>', 'brand': 'Shell'}},
        {'type': 'node', 'id': 3, 'lat': LAT0 - 1500 * KLAT, 'lon': LON0 + 200 * KLON, 'tags': {'amenity': 'fuel', 'brand': 'BR'}}]
# via leste-oeste com 40 km/h, mão dupla; via norte-sul com 60, mão única para o sul; elas se cruzam em (LAT0, LON0+500 m)
WAYS = [{'type': 'way', 'id': 10, 'tags': {'highway': 'residential', 'maxspeed': '40'}, 'geometry': [{'lat': LAT0, 'lon': LON0 - 1000 * KLON}, {'lat': LAT0, 'lon': LON0 + 1500 * KLON}]},
        {'type': 'way', 'id': 11, 'tags': {'highway': 'primary', 'maxspeed': '60 km/h', 'oneway': 'yes'}, 'geometry': [{'lat': LAT0 + 800 * KLAT, 'lon': LON0 + 500 * KLON}, {'lat': LAT0 - 1500 * KLAT, 'lon': LON0 + 500 * KLON}]},
        {'type': 'way', 'id': 12, 'tags': {'highway': 'service', 'maxspeed': 'BR:urban'}, 'geometry': [{'lat': LAT0 + 10 * KLAT, 'lon': LON0}, {'lat': LAT0 + 10 * KLAT, 'lon': LON0 + 100 * KLON}]}]

async def routes(ctx):
    async def overpass(r):
        q = r.request.post_data or ''
        if 'fuel' in q: calls['fuel'] += 1; els = FUEL
        elif 'maxspeed' in q: calls['lim'] += 1; els = WAYS
        else: calls['radar'] += 1; els = []
        await r.fulfill(status=200, headers=CORS, content_type='application/json', body=json.dumps({'elements': els}))
    async def valhalla(r):
        if r.request.method == 'OPTIONS':
            await r.fulfill(status=204, headers=CORS); return
        b = json.loads(r.request.post_data); calls['valhalla'].append(b)
        a, z = b['locations'][0], b['locations'][1]
        trip = {'legs': [{'shape': enc6([(a['lat'], a['lon']), (z['lat'], z['lon'])]), 'maneuvers': [
            {'type': 1, 'instruction': 'Siga.', 'begin_shape_index': 0, 'length': 0.8, 'time': 60}, {'type': 4, 'instruction': 'Chegou.', 'begin_shape_index': 1, 'length': 0, 'time': 0}]}], 'summary': {'length': 0.8, 'time': 60}}
        await r.fulfill(status=200, headers=CORS, content_type='application/json', body=json.dumps({'trip': trip}))
    await ctx.route('https://maps.mail.ru/**', overpass)
    await ctx.route('https://valhalla1.openstreetmap.de/**', valhalla)
    await ctx.route('https://api.open-meteo.com/**', lambda r: r.fulfill(status=503, headers=CORS, body=''))
    await ctx.route('https://api.met.no/**', lambda r: r.fulfill(status=503, headers=CORS, body=''))

FIX = '''([la,lo,v,h,t])=>TN.onPos({timestamp:t,coords:{latitude:la,longitude:lo,altitude:800,accuracy:5,speed:v,heading:h}})'''
MOTION = '''([gx,gy,gz,a,b,c])=>window.dispatchEvent(new DeviceMotionEvent('devicemotion',{accelerationIncludingGravity:{x:gx,y:gy,z:gz},acceleration:{x:0,y:0,z:0},rotationRate:{alpha:a,beta:b,gamma:c},interval:16}))'''

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        ctx = await b.new_context(viewport={'width': 360, 'height': 780})
        await ctx.add_init_script(STUB); await routes(ctx)
        pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(URL); await pg.wait_for_timeout(1200)
        t = 7_000_000

        # ---------- barra: principais + Mais ----------
        r = await pg.evaluate("(()=>{const bot=document.querySelector('#bot');const bs=[...bot.querySelectorAll('.b')];return {n:bs.length,labels:bs.map(b=>b.querySelector('span').textContent),fit:bot.scrollWidth<=bot.clientWidth+1}})()")
        check('barra com 8 botões (Roadbook, Mapa, Ir para, Painel, Telefone, Voz, Gravar, Mais) e cabe em 360 px sem rolar', r['n'] == 8 and r['labels'][-1] == 'Mais' and r['fit'], str(r))
        await pg.click('#bMore'); await pg.wait_for_timeout(200)
        r = await pg.evaluate("[...document.querySelectorAll('#moreGrid .b span')].map(s=>s.textContent)")
        check('"Mais" abre a grade com o resto (13 botões, com Postos e Música)', len(r) == 13 and 'Postos' in r and 'Música' in r and 'Arquivos' in r, str(r))
        await pg.screenshot(path='/tmp/claude-0/-home-user/51ac65f6-457e-5d09-b14e-b860846fbcdb/scratchpad/png/t20_mais.png')
        await pg.click('#moreGrid #bSet'); await pg.wait_for_timeout(300)
        check('tocar em Ajustes na grade abre os Ajustes e fecha a grade', await pg.evaluate("document.querySelector('#dlgSet').open&&!document.querySelector('#dlgMore').open"))

        # ---------- repetições ----------
        r = await pg.evaluate("({rot:document.querySelectorAll('#sRot,#sNavRot').length,mode:document.querySelector('#sRotMode').value,theme:!!document.querySelector('#sTheme'),open:!!document.querySelector('#bOpen'),rad:document.querySelectorAll('#bRadMark,#navRadMark').length,gopen:!!document.querySelector('#dlgGpx #gOpen')})")
        check('um só ajuste de girar o mapa (padrão: só durante o Ir para); sem seletor de tema repetido; Abrir dentro de Arquivos; um só "Marcar radar"',
              r == {'rot': 0, 'mode': 'nav', 'theme': False, 'open': False, 'rad': 1, 'gopen': True}, str(r))
        await pg.select_option('#sRotMode', 'always'); await pg.evaluate("document.querySelector('#dlgSet').close()")
        await pg.evaluate("document.querySelector('[data-pane=paneMap]').click()")
        await pg.evaluate(FIX, [LAT0, LON0, 12, 90, t]); t += 1000
        await pg.evaluate(FIX, [LAT0, LON0 + 12 * KLON, 12, 90, t]); t += 1000; await pg.wait_for_timeout(200)
        check('"sempre": o mapa gira mesmo sem rota', await pg.evaluate("Math.round(TN.map.getBearing())") == 270)
        await pg.evaluate("TN.cfg.rot=false;TN.cfg.navRot=true;TN.applyHeading()")
        check('"só durante o Ir para": sem rota volta ao norte', await pg.evaluate("Math.round(TN.map.getBearing())") == 0)
        await pg.evaluate("document.querySelector('#bMore').click()"); await pg.wait_for_timeout(150)
        await pg.click('#moreGrid #bDay'); await pg.wait_for_timeout(150)
        check('tema pelo botão de "Mais", que mostra o modo atual', (await pg.text_content('#dayTxt')).startswith('Tema: '))
        await pg.evaluate("document.querySelector('#bMore').click()"); await pg.wait_for_timeout(150)
        await pg.click('#moreGrid #bGpx'); await pg.wait_for_timeout(300)
        async with pg.expect_file_chooser() as fc:
            await pg.click('#gOpen')
        check('"Abrir PDF ou GPX" em Arquivos abre o seletor de arquivo', (await fc.value) is not None and not await pg.evaluate("document.querySelector('#dlgGpx').open"))
        n0 = await pg.evaluate("TN.radars.size")
        await pg.evaluate("TN.runCmd(TN.parseCmd('marcar radar'))")
        check('"Trilha, marcar radar" marca sem precisar tocar', await pg.evaluate("TN.radars.size") == n0 + 1 and (await pg.evaluate("TN.spoken.slice(-1)[0]")) == 'Radar marcado')

        # ---------- postos ----------
        await pg.evaluate("document.querySelector('#bMore').click()"); await pg.wait_for_timeout(150)
        await pg.click('#moreGrid #bFuel'); await pg.wait_for_timeout(1500)
        r = await pg.evaluate("({info:document.querySelector('#fuelInfo').textContent,rows:[...document.querySelectorAll('#fuelList .lr b')].map(b=>b.textContent),html:document.querySelector('#fuelList').innerHTML,mk:document.querySelectorAll('.fuelmk').length})")
        check('Postos: lista do mais perto ao mais longe, nome vindo da internet escapado, marcadores no mapa',
              r['rows'] == ['Posto <b>Perto</b>', 'BR', 'Posto Longe'] and '&lt;b&gt;' in r['html'] and r['mk'] == 3 and r['info'].startswith('3 postos'), str(r)[:240])
        await pg.click('#fuelList [data-fgo="0"]'); await pg.wait_for_timeout(1500)
        check('"Ir" faz a rota até o posto', await pg.evaluate("TN.nav&&TN.nav.to.name") == 'Posto <b>Perto</b>')
        await pg.evaluate("TN.navStop()")
        c = await pg.evaluate("['posto mais perto','preciso abastecer','gasolina'].map(t=>TN.parseCmd(t).a)")
        check('voz: "posto mais perto", "preciso abastecer", "gasolina" → postos', c == ['fuel', 'fuel', 'fuel'], str(c))
        await pg.evaluate("TN.runCmd(TN.parseCmd('posto mais perto'))"); await pg.wait_for_timeout(2500)
        sp = await pg.evaluate("TN.spoken.slice(-3)")
        check('"Trilha, posto mais perto": fala o posto e a distância e já começa a rota', any(x.startswith('Posto mais perto: Posto <b>Perto</b>, a 800 metros') for x in sp) and await pg.evaluate("!!TN.nav"), str(sp))
        await pg.evaluate("TN.navStop()")

        # ---------- limite da via ----------
        for i in range(3):
            await pg.evaluate(FIX, [LAT0 + 3 * KLAT, LON0 + (300 + i * 10) * KLON, 11, 90, t]); t += 2000
        await pg.wait_for_timeout(1500)
        await pg.evaluate(FIX, [LAT0 + 3 * KLAT, LON0 + 340 * KLON, 11, 90, t]); t += 2000
        r = await pg.evaluate("({on:document.querySelector('#limBox').classList.contains('on'),v:document.querySelector('#limBox').textContent,cur:TN.limCur})")
        check('na rua leste-oeste: placa 40 (dados do OSM baixados)', calls['lim'] >= 1 and r == {'on': True, 'v': '40', 'cur': 40}, f"{calls['lim']} {r}")
        await pg.evaluate(FIX, [LAT0 + 3 * KLAT, LON0 + 360 * KLON, 55, 90, t]); t += 2000
        r = await pg.evaluate("({b:document.querySelector('#banner').textContent,over:document.querySelector('#limBox').classList.contains('over')})")
        check('a 55 km/h (40 + 7 de tolerância): alerta "LIMITE 40" e placa piscando', 'LIMITE 40' in r['b'] and r['over'], str(r))
        check('voz: "Velocidade acima do limite. Limite 40"', 'Velocidade acima do limite. Limite 40' in await pg.evaluate("TN.spoken"))
        await pg.evaluate(FIX, [LAT0 - 200 * KLAT, LON0 + 503 * KLON, 30, 180, t]); t += 2000
        check('na avenida norte-sul (mão única, sentido certo): placa 60 ("60 km/h" no OSM)', await pg.evaluate("TN.limCur") == 60)
        await pg.evaluate(FIX, [LAT0 - 220 * KLAT, LON0 + 503 * KLON, 30, 0, t]); t += 2000
        check('na contramão da mão única: não mostra o limite dela', await pg.evaluate("TN.limCur") != 60)
        await pg.evaluate(FIX, [LAT0 - 900 * KLAT, LON0 - 900 * KLON, 30, 90, t]); t += 2000
        check('longe de qualquer via com limite: placa some', not await pg.evaluate("document.querySelector('#limBox').classList.contains('on')"))
        await pg.evaluate("TN.cfg.limOn=false")
        await pg.evaluate(FIX, [LAT0 + 3 * KLAT, LON0 + 350 * KLON, 55, 90, t]); t += 2000
        check('desligado nos Ajustes: sem placa e sem alerta da via', not await pg.evaluate("document.querySelector('#limBox').classList.contains('on')") and 'LIMITE 40' not in await pg.text_content('#banner'))
        await pg.evaluate("TN.cfg.limOn=true")

        # ---------- inclinação ----------
        await pg.evaluate(FIX, [LAT0 + 3 * KLAT, LON0 + 360 * KLON, 0, None, t]); t += 1000
        for _ in range(5): await pg.evaluate(MOTION, [0, 0, 9.81, 0, 0, 0])
        check('parado: calibra a vertical da moto', await pg.evaluate("!!TN.lean.g0"))
        await pg.evaluate(FIX, [LAT0 + 3 * KLAT, LON0 + 370 * KLON, 10, 90, t]); t += 1000
        w = math.degrees(math.tan(math.radians(30)) * 9.81 / 10)     # guinada que dá 30° a 36 km/h
        for _ in range(40): await pg.evaluate(MOTION, [0, 0, 9.81, w, 0, 0])
        r = await pg.evaluate("({v:TN.lean.v,txt:TN.leanTxt(),maxL:TN.lean.maxL})")
        check('curva à esquerda a 36 km/h com guinada de %.1f°/s → ~30° E' % w, abs(r['v'] - 30) < 1.5 and r['txt'] == '30° E' and abs(r['maxL'] - 30) < 1.5, str(r))
        for _ in range(40): await pg.evaluate(MOTION, [0, 0, 9.81, -w * 0.7, 0, 0])
        r = await pg.evaluate("({txt:TN.leanTxt(),maxR:Math.round(TN.lean.maxR)})")
        check('curva à direita mais leve → ~22° D, máximo da direita guardado', r['txt'] in ('22° D', '21° D', '23° D') and 20 <= r['maxR'] <= 23, str(r))
        await pg.evaluate("document.querySelector('[data-pane=paneDash]').click()"); await pg.evaluate(FIX, [LAT0 + 3 * KLAT, LON0 + 380 * KLON, 10, 90, t]); t += 1000
        dash = await pg.text_content('#dash')
        check('Painel mostra Inclinação e Inclinação máxima', 'INCLINAÇÃO' in dash and 'E 30° · D' in dash, dash[-160:])

        # ---------- cronômetro foi para "Mais": rodando, aparece em cima ----------
        await pg.evaluate("document.querySelector('#bMore').click()"); await pg.wait_for_timeout(150)
        await pg.dispatch_event('#moreGrid #bChrono', 'pointerdown'); await pg.dispatch_event('#moreGrid #bChrono', 'pointerup'); await pg.wait_for_timeout(1200)
        check('cronômetro rodando aparece na barra de cima', await pg.is_visible('#chronoTop') and (await pg.text_content('#chronoTop')).startswith('⏱ 00:0'))
        await pg.screenshot(path='/tmp/claude-0/-home-user/51ac65f6-457e-5d09-b14e-b860846fbcdb/scratchpad/png/t20.png')
        check('sem erros de página', not errs, str(errs[:3]))
        await b.close()
    print('\nRESULTADO:', 'tudo certo' if not FAILS else 'FALHAS: ' + '; '.join(FAILS))
    sys.exit(1 if FAILS else 0)

asyncio.run(main())
