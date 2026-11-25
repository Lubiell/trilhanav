"""v2.4: mapa gira sozinho durante o "Ir para" (o "Trilha, ir para <lugar>" por voz saiu na v2.7.4) e clima/temperatura com alertas.
Photon, Valhalla, Open-Meteo e MET Norway simulados com page.route (nada de internet de verdade no teste)."""
import asyncio, json, math, sys
from urllib.parse import unquote
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html'
FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

STUB = "window.__spk=[];Object.defineProperty(window,'speechSynthesis',{value:{speak:u=>window.__spk.push(u.text),cancel(){},getVoices(){return []}},configurable:true});window.SpeechSynthesisUtterance=function(t){this.text=t};"
LAT0, LON0 = -19.9200, -43.9400
KLON = 1 / (111194.9 * math.cos(math.radians(LAT0))); KLAT = 1 / 111194.9
PTS = [(LAT0, LON0 + i * 20 * KLON) for i in range(31)] + [(LAT0 - i * 20 * KLAT, LON0 + 600 * KLON) for i in range(1, 26)]
DEST = PTS[-1]

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

TRIP = {'legs': [{'shape': enc6(PTS), 'maneuvers': [
    {'type': 1, 'instruction': 'Siga para o leste.', 'begin_shape_index': 0, 'length': 0.6, 'time': 50},
    {'type': 10, 'instruction': 'Vire à direita na Rua B.', 'street_names': ['Rua B'], 'begin_shape_index': 30, 'length': 0.5, 'time': 40},
    {'type': 4, 'instruction': 'Você chegou ao seu destino.', 'begin_shape_index': len(PTS) - 1, 'length': 0, 'time': 0}]}], 'summary': {'length': 1.1, 'time': 3700}}

calls = {'photon': [], 'valhalla': 0, 'om': [], 'met': 0}
MODE = {'om': 'ok', 'dest_rain': False}
CORS = {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'content-type', 'Access-Control-Allow-Methods': 'POST, GET'}

def om_body(lat):
    rain_dest = MODE['dest_rain'] and abs(lat - round(DEST[0], 2)) < 0.006
    return {'current': {'temperature_2m': 27.4, 'apparent_temperature': 29.1, 'weather_code': 2, 'wind_gusts_10m': 72.0},
            'minutely_15': {'precipitation': [0, 0, 0.6, 1.2, 0, 0, 0, 0]},
            'hourly': {'precipitation_probability': [10, 80, 90, 20] + [0] * 8, 'weather_code': [2, 61, 63, 3] + [1] * 8,
                       'temperature_2m': [27, 25, 23, 24] + [24] * 8, 'wind_gusts_10m': [72, 40, 30, 20] + [10] * 8}} if not rain_dest else \
           {'current': {'temperature_2m': 22, 'apparent_temperature': 22, 'weather_code': 1, 'wind_gusts_10m': 10},
            'minutely_15': {'precipitation': [0] * 8},
            'hourly': {'precipitation_probability': [0, 90] + [0] * 10, 'weather_code': [1, 95] + [1] * 10, 'temperature_2m': [22] * 12, 'wind_gusts_10m': [10] * 12}}

async def routes(ctx):
    async def photon(r):
        calls['photon'].append(r.request.url)
        f = {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [DEST[1], DEST[0]]}, 'properties': {'name': 'Praça da Estação', 'city': 'Belo Horizonte'}}
        await r.fulfill(status=200, headers=CORS, content_type='application/json', body=json.dumps({'features': [f]}))
    async def valhalla(r):
        if r.request.method == 'OPTIONS':
            await r.fulfill(status=204, headers=CORS); return
        calls['valhalla'] += 1
        await r.fulfill(status=200, headers=CORS, content_type='application/json', body=json.dumps({'trip': TRIP}))
    async def om(r):
        u = r.request.url; calls['om'].append(u)
        if MODE['om'] == 'quota':
            await r.fulfill(status=429, headers=CORS, content_type='application/json', body='{"reason":"Daily API request limit exceeded.","error":true}'); return
        lat = float(u.split('latitude=')[1].split('&')[0])
        await r.fulfill(status=200, headers=CORS, content_type='application/json', body=json.dumps(om_body(lat)))
    async def met(r):
        calls['met'] += 1
        ts = [{'data': {'instant': {'details': {'air_temperature': 18.5 - i * 0.1, 'wind_speed': 3.0}}, 'next_1_hours': {'summary': {'symbol_code': 'heavyrain' if i == 0 else 'cloudy'}, 'details': {'precipitation_amount': 2.0 if i == 0 else 0}}}} for i in range(12)]
        await r.fulfill(status=200, headers=CORS, content_type='application/json', body=json.dumps({'properties': {'timeseries': ts}}))
    await ctx.route('https://photon.komoot.io/**', photon)
    await ctx.route('https://valhalla1.openstreetmap.de/**', valhalla)
    await ctx.route('https://api.open-meteo.com/**', om)
    await ctx.route('https://api.met.no/**', met)
    await ctx.route('https://maps.mail.ru/**', lambda r: r.fulfill(status=200, headers=CORS, content_type='application/json', body='{"elements":[]}'))

FIX = '''([la,lo,v,h,t])=>TN.onPos({timestamp:t,coords:{latitude:la,longitude:lo,altitude:800,accuracy:5,speed:v,heading:h}})'''

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        ctx = await b.new_context(viewport={'width': 1280, 'height': 720})
        await ctx.add_init_script(STUB); await routes(ctx)
        pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(URL); await pg.wait_for_timeout(1000)
        spoken = lambda: pg.evaluate('TN.spoken.slice()')
        t = 5_000_000
        await pg.evaluate(FIX, [LAT0, LON0, 0, None, t]); t += 1000
        await pg.wait_for_timeout(3500)

        # ---------- clima: privacidade ----------
        check('sem aceitar o aviso de internet, nenhum pedido de clima', not calls['om'] and not calls['met'])
        check('temperatura lá em cima pede para ligar ("?")', await pg.text_content('#wx') == '🌡️ ?')
        await pg.click('#wx'); await pg.wait_for_timeout(300)
        check('tocar na temperatura mostra o aviso (que cita o clima)', await pg.is_visible('#dlgAsk') and 'Open-Meteo' in await pg.text_content('#askMsg'))
        await pg.click('#askOk'); await pg.wait_for_timeout(1500)

        # ---------- clima: dados e alertas ----------
        q = calls['om'][-1] if calls['om'] else ''
        check('pede o clima com a posição arredondada (0,01°)', 'latitude=-19.92&longitude=-43.94' in q, q[:90])
        r = await pg.evaluate("({wx:document.querySelector('#wx').textContent,al:document.querySelector('#wx').classList.contains('alert'),now:document.querySelector('#wxNow').textContent,n:document.querySelectorAll('#wxHours .lr').length,src:document.querySelector('#wxSrc').textContent})")
        check('barra de cima: ícone + temperatura, vermelha com alerta', r['wx'] == '☁️ 27°' and r['al'], str(r))
        check('tela do clima: agora, sensação, rajadas, 12 horas e a fonte', 'sensação 29°' in r['now'] and 'rajadas 72 km/h' in r['now'] and r['n'] == 12 and 'Open-Meteo (CC BY 4.0)' in r['src'], str(r))
        sp = await spoken()
        check('voz: chuva chegando (em cerca de 30 min) e rajadas de 72 km/h', 'Chuva prevista em cerca de 30 minutos' in sp and 'Rajadas de vento de até 72 quilômetros por hora' in sp, str(sp[-3:]))
        n0 = len(sp)
        await pg.click('#wxRefresh'); await pg.wait_for_timeout(1500)
        check('mesmo alerta não se repete dentro de 1 hora', len(await spoken()) == n0)
        await pg.evaluate("document.querySelector('#dlgWx').close()")
        MODE['om'] = 'quota'
        await pg.evaluate("TN.wxUpdate(true)"); await pg.wait_for_timeout(2500)
        d = await pg.evaluate("TN.wxD")
        check('cota do Open-Meteo estourada: usa o MET Norway', calls['met'] >= 1 and d['src'] == 'MET Norway' and d['kind'] == 'rain' and round(d['temp']) == 18, str({k: d[k] for k in ('src', 'kind', 'temp')}))
        MODE['om'] = 'ok'
        await pg.evaluate("TN.wxUpdate(true)"); await pg.wait_for_timeout(1500)
        c = await pg.evaluate("[TN.parseCmd('clima'),TN.parseCmd('ir para a Praça da Estação'),TN.parseCmd('encerrar rota')]")
        check('"clima", "ir para" e "encerrar rota" por voz saíram (voz só para música)', c == [None, None, None], str(c))

        # ---------- "Ir para" pela tela ----------
        await pg.evaluate("TN.cfg.wx=true")
        MODE['dest_rain'] = True
        await pg.evaluate("TN.openNavDlg()"); await pg.wait_for_timeout(300)
        await pg.fill('#navQ', 'Praça da Estação'); await pg.press('#navQ', 'Enter'); await pg.wait_for_timeout(1500)
        await pg.click('#navRes [data-i="0"]'); await pg.wait_for_timeout(1500)
        await pg.click('#navRoutes [data-go="0"]'); await pg.wait_for_timeout(800)
        r = await pg.evaluate("({nav:!!TN.nav,to:TN.nav&&TN.nav.to.name,map:document.querySelector('#paneMap').classList.contains('on')})")
        check('"Ir para" procura o lugar e começa a rota', r == {'nav': True, 'to': 'Praça da Estação', 'map': True} and 'q=praça da estação' in unquote(calls['photon'][-1]).lower() and calls['valhalla'] == 1, str((r, calls['valhalla'])))
        sp = await spoken()
        check('previsão no destino: "Tempestade prevista no destino por volta das HH:MM"', any(x.startswith('Tempestade prevista no destino por volta das') for x in sp), str(sp[-3:]))

        # ---------- mapa gira durante a rota ----------
        await pg.evaluate(FIX, [PTS[3][0], PTS[3][1], 12, 90, t]); t += 1000
        await pg.wait_for_timeout(200)
        b1 = await pg.evaluate("Math.round(TN.map.getBearing())")
        check('durante a rota o mapa gira com a direção (rumo 90° → mapa a 270°), mesmo com "Mapa gira" desligado', b1 == 270 and not await pg.evaluate('TN.cfg.rot'), str(b1))
        await pg.evaluate("document.querySelector('#navEnd').click()"); await pg.wait_for_timeout(200)
        await pg.evaluate("document.querySelector('#askOk').click()"); await pg.wait_for_timeout(200)   # 2.7.10: o Sair pergunta antes
        b2 = await pg.evaluate("Math.round(TN.map.getBearing())")
        check('"Sair" encerra a rota e o mapa volta ao norte', not await pg.evaluate('!!TN.nav') and b2 == 0, str(b2))
        await pg.evaluate("TN.cfg.navRot=false"); await pg.evaluate("TN.openNavDlg()"); await pg.wait_for_timeout(300)
        await pg.click('#navRecent [data-rc="0"]'); await pg.wait_for_timeout(1500); await pg.click('#navRoutes [data-go="0"]'); await pg.wait_for_timeout(500)
        await pg.evaluate(FIX, [PTS[5][0], PTS[5][1], 12, 90, t]); t += 1000
        check('com "Mapa gira durante a rota" desligado, não gira', await pg.evaluate("Math.round(TN.map.getBearing())") == 0)
        check('destino dos recentes é usado sem nova busca', len(calls['photon']) == 1)

        # ---------- celular: temperatura cabe na barra de cima ----------
        await pg.set_viewport_size({'width': 360, 'height': 780}); await pg.wait_for_timeout(400)
        r = await pg.evaluate("(()=>{const t=document.querySelector('#top');return {sw:t.scrollWidth,cw:t.clientWidth}})()")
        check('barra de cima com a temperatura cabe em 360 px', r['sw'] <= r['cw'] + 1, str(r))
        await pg.screenshot(path='/tmp/claude-0/-home-user/51ac65f6-457e-5d09-b14e-b860846fbcdb/scratchpad/png/t19.png')
        check('sem erros de página', not errs, str(errs[:3]))
        await b.close()
    print('\nRESULTADO:', 'tudo certo' if not FAILS else 'FALHAS: ' + '; '.join(FAILS))
    sys.exit(1 if FAILS else 0)

asyncio.run(main())
