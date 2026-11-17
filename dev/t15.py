"""v2.1: modo cidade (busca, rota por ruas, voz curva a curva, recálculo, chegada), radares do OpenStreetMap, ícones e ajustes de tela.
Os serviços externos (Photon, Valhalla, Overpass) são simulados com page.route: o teste não depende da internet nem gasta a cota deles."""
import asyncio, json, math, sys
from playwright.async_api import async_playwright

URL = 'http://localhost:8765/index.html'
FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

STUB = "window.__spk=[];window.__open=[];window.open=(u)=>{window.__open.push(u);return null};Object.defineProperty(window,'speechSynthesis',{value:{speak:u=>window.__spk.push(u.text),cancel(){},getVoices(){return []}},configurable:true});window.SpeechSynthesisUtterance=function(t){this.text=t};"

# rota em L: 600 m para leste, vira à direita, 500 m para o sul (BH)
LAT0, LON0 = -19.9200, -43.9400
KLON = 1 / (111194.9 * math.cos(math.radians(LAT0)))
KLAT = 1 / 111194.9
leg1 = [(LAT0, LON0 + i * 20 * KLON) for i in range(31)]            # 0..600 m
c = leg1[-1]
leg2 = [(c[0] - i * 20 * KLAT, c[1]) for i in range(1, 26)]          # +500 m
PTS = leg1 + leg2
DEST = PTS[-1]

def enc6(pts):
    out, pl, po = [], 0, 0
    for la, lo in pts:
        a, b = round(la * 1e6), round(lo * 1e6)
        for v in (a - pl, b - po):
            v = ~(v << 1) if v < 0 else v << 1
            while v >= 0x20:
                out.append(chr((0x20 | (v & 0x1f)) + 63)); v >>= 5
            out.append(chr(v + 63))
        pl, po = a, b
    return ''.join(out)

def trip(pts, alt=False):
    n = len(pts)
    man = [{'type': 1, 'instruction': 'Siga para o leste na Rua A.', 'verbal_pre_transition_instruction': 'Siga para o leste na Rua A.', 'street_names': ['Rua A'], 'begin_shape_index': 0, 'end_shape_index': 30, 'length': 0.6, 'time': 50},
           {'type': 10, 'instruction': 'Vire à direita na Rua B.', 'verbal_transition_alert_instruction': 'Vire à direita na Rua B.', 'verbal_pre_transition_instruction': 'Vire à direita na Rua B.', 'street_names': ['Rua B'], 'begin_shape_index': 30, 'end_shape_index': n - 1, 'length': 0.5, 'time': 40},
           {'type': 4, 'instruction': 'Você chegou ao seu destino.', 'verbal_pre_transition_instruction': 'Você chegou ao seu destino.', 'begin_shape_index': n - 1, 'end_shape_index': n - 1, 'length': 0, 'time': 0}]
    if alt:
        man[1]['street_names'] = ['Avenida Alternativa']; man[1]['length'] = 0.9
    return {'legs': [{'shape': enc6(pts), 'maneuvers': man}], 'summary': {'length': 1.1, 'time': 120 if alt else 90}}

ALT = [(LAT0, LON0)] + [(LAT0 - i * 20 * KLAT, LON0) for i in range(1, 26)] + [(LAT0 - 500 * KLAT, LON0 + i * 20 * KLON) for i in range(1, 31)]
RADAR = (c[0] - 300 * KLAT, c[1] + 3 * KLON)        # na Rua B, 300 m depois da curva, 3 m ao lado
calls = {'photon': 0, 'valhalla': 0, 'overpass': 0, 'bodies': []}
MODE = {'valhalla': 'ok'}

async def routes(ctx):
    async def photon(route):
        calls['photon'] += 1
        feats = [{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [DEST[1], DEST[0]]}, 'properties': {'name': 'Praça <b>Teste</b>', 'street': 'Rua B', 'city': 'Belo Horizonte', 'state': 'Minas Gerais'}},
                 {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [-43.95, -19.93]}, 'properties': {'street': 'Rua C', 'housenumber': '10', 'city': 'Belo Horizonte'}}]
        await route.fulfill(status=200, headers={'Access-Control-Allow-Origin': '*'}, content_type='application/json', body=json.dumps({'features': feats}))
    async def valhalla(route):
        if route.request.method == 'OPTIONS':
            await route.fulfill(status=204, headers={'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'content-type', 'Access-Control-Allow-Methods': 'POST'}); return
        calls['valhalla'] += 1; calls['bodies'].append(json.loads(route.request.post_data or '{}'))
        if MODE['valhalla'] == 'fail':
            await route.fulfill(status=500, headers={'Access-Control-Allow-Origin': '*'}, body='erro'); return
        body = json.loads(route.request.post_data)
        st = body['locations'][0]
        if MODE['valhalla'] == 'reroute':     # da posição atual até o destino, em linha
            pts = [(st['lat'], st['lon'])] + PTS[35:]
            out = {'trip': trip(pts)}
        else:
            out = {'trip': trip(ALT, True), 'alternates': [{'trip': trip(PTS)}]}   # o Valhalla manda a mais lenta primeiro às vezes
        await route.fulfill(status=200, headers={'Access-Control-Allow-Origin': '*'}, content_type='application/json', body=json.dumps(out))
    async def overpass(route):
        calls['overpass'] += 1
        els = [{'type': 'node', 'id': 111, 'lat': RADAR[0], 'lon': RADAR[1], 'tags': {'highway': 'speed_camera', 'maxspeed': '60'}},
               {'type': 'node', 'id': 222, 'lat': LAT0 + 0.003, 'lon': LON0 - 0.003, 'tags': {'highway': 'speed_camera', 'maxspeed': '40 km/h'}},
               {'type': 'node', 'id': 333, 'lat': LAT0, 'lon': LON0, 'tags': {'highway': 'speed_camera', 'maxspeed': '<img src=x onerror=alert(1)>'}}]
        await route.fulfill(status=200, headers={'Access-Control-Allow-Origin': '*'}, content_type='application/json', body=json.dumps({'elements': els}))
    await ctx.route('https://photon.komoot.io/**', photon)
    await ctx.route('https://valhalla1.openstreetmap.de/**', valhalla)
    await ctx.route('https://maps.mail.ru/**', overpass)
    # clima fora do ar no teste (nada de internet de verdade)
    await ctx.route('https://api.open-meteo.com/**', lambda r: r.fulfill(status=503, body=''))
    await ctx.route('https://api.met.no/**', lambda r: r.fulfill(status=503, body=''))

FIX = '''([la,lo,v,h,t,acc])=>TN.onPos({timestamp:t,coords:{latitude:la,longitude:lo,altitude:800,accuracy:acc||5,speed:v,heading:h}})'''

async def drive(pg, pts, v, t0, h):
    for i, (la, lo) in enumerate(pts):
        await pg.evaluate(FIX, [la, lo, v, h(i), t0 + i * 1000, 5])
    return t0 + len(pts) * 1000

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        ctx = await b.new_context(viewport={'width': 1280, 'height': 720})
        await ctx.add_init_script(STUB)
        await routes(ctx)
        pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('dialog', lambda d: (errs.append('DIALOG ' + d.message), asyncio.ensure_future(d.dismiss())))
        await pg.goto(URL); await pg.wait_for_timeout(1200)

        # ---------- ícones e barra ----------
        r = await pg.evaluate('''(()=>{const bs=[...document.querySelectorAll('#bot .b, #moreGrid .b')];return {n:bs.length,svg:bs.filter(b=>b.querySelector('svg.ic use')).length,
          emoji:bs.filter(b=>/\\p{Extended_Pictographic}/u.test([...b.childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent).join(''))).length,
          refs:bs.map(b=>b.querySelector('use')&&b.querySelector('use').getAttribute('href')).filter(h=>!document.querySelector(h)).length}})()''')
        check('barra de baixo: todos os botões com ícone SVG, sem emoji, sem símbolo faltando', r['n'] >= 21 and r['svg'] == r['n'] and r['emoji'] == 0 and r['refs'] == 0, str(r))
        check('dec6 decodifica a polyline do Valhalla', await pg.evaluate('(s)=>{const p=TN.dec6(s);return p.length+"|"+p[30].lat.toFixed(6)+"|"+p[30].lon.toFixed(6)}', enc6(PTS)) == f'{len(PTS)}|{c[0]:.6f}|{c[1]:.6f}')

        # ---------- privacidade: nada sai antes do aviso ----------
        await pg.evaluate(FIX, [LAT0, LON0, 0, None, 1_000_000, 5]); await pg.wait_for_timeout(1500)
        check('sem aceitar o aviso, nenhum pedido a Photon/Valhalla/Overpass (nem de radar)', calls['photon'] + calls['valhalla'] + calls['overpass'] == 0, str(calls))

        # ---------- busca e rotas ----------
        await pg.click('#bNav'); await pg.wait_for_timeout(300)
        check('primeiro uso mostra o aviso de privacidade', await pg.is_visible('#dlgAsk') and 'OpenStreetMap' in await pg.text_content('#askMsg'))
        await pg.click('#askOk'); await pg.wait_for_timeout(300)
        await pg.fill('#navQ', 'praça teste'); await pg.wait_for_timeout(1600)
        res = await pg.evaluate("[...document.querySelectorAll('#navRes [data-i]')].map(e=>e.innerHTML)")
        check('busca mostra os resultados do Photon', len(res) == 2 and calls['photon'] == 1, str(calls))
        check('nome vindo da internet é escapado (sem HTML injetado)', '&lt;b&gt;Teste&lt;/b&gt;' in res[0] and '<b>Teste</b>' not in res[0].replace('<b>Praça', ''), res[0][:120])
        await pg.click('#navRes [data-i="0"]'); await pg.wait_for_timeout(1500)
        rows = await pg.evaluate("[...document.querySelectorAll('#navRoutes [data-go]')].length")
        txt = await pg.text_content('#navRoutes')
        bd = calls['bodies'][-1]
        check('duas rotas, a mais rápida primeiro, com tempo, km e "via"', rows == 2 and txt.index('via Rua A') < txt.index('via Avenida Alternativa') and txt.index('(mais rápida)') < txt.index('via Rua A'), txt[:160])
        check('pedido ao Valhalla: moto, pt-BR, alternativas, sem trilhas', bd.get('costing') == 'motorcycle' and bd['directions_options']['language'] == 'pt-BR' and bd['alternates'] == 2 and bd['costing_options']['motorcycle']['use_trails'] == 0, json.dumps(bd)[:200])
        check('destino entra nos recentes', 'Praça' in await pg.text_content('#navRecent'))
        await pg.click('#sNavToll'); await pg.wait_for_timeout(1500)
        check('"evitar pedágio" recalcula com use_tolls=0', calls['bodies'][-1]['costing_options']['motorcycle']['use_tolls'] == 0)
        await pg.click('#navRoutes [data-ext="waze"]')
        check('Abrir no Waze usa o link universal do Waze', await pg.evaluate('window.__open.slice(-1)[0]') == f'https://waze.com/ul?ll={DEST[0]:.6f},{DEST[1]:.6f}&navigate=yes')
        await pg.click('#navRoutes [data-go="0"]'); await pg.wait_for_timeout(600)
        st = await pg.evaluate("({nav:!!TN.nav,on:document.body.classList.contains('navOn'),card:getComputedStyle(document.querySelector('#navCard')).display,pane:document.querySelector('#paneMap').classList.contains('on'),dlg:document.querySelector('#dlgNav').open})")
        check('Ir: começa a navegação, mostra o cartão e o mapa, fecha a tela', st == {'nav': True, 'on': True, 'card': 'grid', 'pane': True, 'dlg': False}, str(st))
        spk = await pg.evaluate('TN.spoken.slice(-1)[0]')
        check('fala o resumo da rota', spk.startswith('Rota para Praça') and 'quilômetro' in spk, spk)

        r = await pg.evaluate("""()=>{const t={legs:[{shape:TN.dec6?'':'',maneuvers:[]}]};const rt=TN.parseTrip({legs:[{shape:%s,maneuvers:[{type:26,instruction:'Enter Praça Raul Soares and take the 2ª exit onto Avenida Amazonas.',verbal_pre_transition_instruction:'Enter Praça Raul Soares and take the 2ª exit onto Avenida Amazonas.',roundabout_exit_count:2,street_names:['Praça Raul Soares'],roundabout_exit_street_names:['Avenida Amazonas'],begin_shape_index:3},{type:27,instruction:'Exit the roundabout onto Avenida Amazonas.',street_names:['Avenida Amazonas'],begin_shape_index:5},{type:10,instruction:'Turn right onto Rua X.',street_names:['Rua X'],begin_shape_index:8}]}],summary:{time:60}});return rt.man.map(m=>m.txt+' | '+m.pre)}""" % json.dumps(enc6(PTS)))
        check('rotatória e frases em inglês do Valhalla viram português', r == ['Na rotatória, pegue a 2ª saída para Avenida Amazonas. | Na rotatória, pegue a 2ª saída para Avenida Amazonas.', 'Saia da rotatória para Avenida Amazonas. | Saia da rotatória para Avenida Amazonas.', 'Vire à direita para Rua X. | Vire à direita para Rua X.'], str(r))

        # ---------- radares baixados da área ----------
        await pg.wait_for_timeout(2500)
        nr = await pg.evaluate('TN.radars.size')
        check('radares da área da rota baixados do Overpass', calls['overpass'] >= 1 and nr == 3, f'{calls} radares={nr}')
        lim = await pg.evaluate("[...TN.radars.values()].map(r=>r.max).sort().join(',')")
        check('limite lido do maxspeed ("60", "40 km/h"; lixo vira vazio)', lim in ('40,60,', '40,60,null'), lim)

        # ---------- dirigindo: voz, cartão, radar ----------
        t = await drive(pg, PTS[1:12], 15, 2_000_000, lambda i: 90)
        sp = await pg.evaluate('TN.spoken')
        card = await pg.evaluate("({d:document.querySelector('#navDist').textContent,t:document.querySelector('#navTxt').textContent,s:document.querySelector('#navSub').textContent,eta:document.querySelector('#navEta').textContent,img:document.querySelector('#navArr').src.slice(0,30)})")
        check('aviso antecipado da curva ("Em N metros, vire à direita na Rua B.")', any(s.startswith('Em ') and 'vire à direita na Rua B' in s for s in sp), str(sp[-3:]))
        check('cartão: distância até a curva, instrução, rua, hora de chegada', card['t'] == 'Vire à direita na Rua B.' and card['d'].endswith(' m') and card['s'] == 'Rua B' and ':' in card['eta'] and card['img'].startswith('data:image/svg'), str(card))
        check('CAP do painel lateral segue a rota', (await pg.text_content('#wpLabel')).startswith('ROTA:'))
        t = await drive(pg, PTS[12:31], 15, t, lambda i: 90)
        sp = await pg.evaluate('TN.spoken')
        check('instrução na hora da curva', 'Vire à direita na Rua B.' in sp, str(sp[-4:]))
        n0 = len(sp)
        t = await drive(pg, PTS[31:33], 15, t, lambda i: 180)
        sp = await pg.evaluate('TN.spoken')
        rb = await pg.evaluate("({on:document.querySelector('#radBox').classList.contains('on'),lim:document.querySelector('#radLim').textContent,d:document.querySelector('#radDist').textContent})")
        check('radar à frente na rota: placa com limite e distância', rb['on'] and rb['lim'] == '60', str(rb))
        rv = [s for s in sp if s.startswith('Radar em')]
        check('voz avisa o radar com o limite, a no máximo 600 m pela rota', len(rv) == 1 and 'limite 60' in rv[0] and int(rv[0].split()[2]) <= 600, str(rv))
        await pg.evaluate(FIX, [PTS[34][0], PTS[34][1], 22, 180, t, 5]); t += 1000
        bn = await pg.evaluate("({b:document.querySelector('#banner').textContent,v:document.querySelector('#banner').style.display,over:document.querySelector('#radBox').classList.contains('over')})")
        check('acima do limite (79 km/h > 60+7): faixa vermelha e placa piscando', 'RADAR 60' in bn['b'] and bn['v'] == 'block' and bn['over'], str(bn))
        check('um só aviso de voz por radar', sum(1 for s in (await pg.evaluate('TN.spoken')) if s.startswith('Radar em')) == 1)

        # ---------- fora da rota: recálculo ----------
        MODE['valhalla'] = 'reroute'; v0 = calls['valhalla']
        off = [(PTS[35][0], PTS[35][1] + 150 * KLON * k / 3) for k in (3, 3, 3, 3)]
        for i, (la, lo) in enumerate(off):
            await pg.evaluate(FIX, [la, lo, 8, 90, t, 5]); t += 1000
        await pg.wait_for_timeout(1800)
        sp = await pg.evaluate('TN.spoken')
        check('3 posições a 150 m da rota recalculam (um pedido só)', calls['valhalla'] == v0 + 1 and 'Rota recalculada' in sp, f'{calls["valhalla"] - v0} pedidos')
        # ---------- chegada ----------
        await pg.evaluate(FIX, [DEST[0], DEST[1], 2, 180, t, 5]); t += 1000
        sp = await pg.evaluate('TN.spoken')
        check('chegada: "Você chegou ao destino"', 'Você chegou ao destino' in sp)
        await pg.wait_for_timeout(6500)
        check('depois da chegada a rota se encerra sozinha', await pg.evaluate("!TN.nav&&!document.body.classList.contains('navOn')"))

        # ---------- radar sem rota (rumo do GPS) ----------
        await pg.evaluate("TN.spoken.length=0")
        await pg.evaluate("()=>{for(const [id] of TN.radars)if(id!=='o111')TN.radars.delete(id)}")
        base = (RADAR[0] + 450 * KLAT, RADAR[1] - 3 * KLON)
        await pg.evaluate(FIX, [base[0], base[1], 12, 180, t, 5]); t += 1000
        await pg.evaluate(FIX, [base[0] - 12 * KLAT, base[1], 12, 180, t, 5]); t += 1000
        on1 = await pg.evaluate("document.querySelector('#radBox').classList.contains('on')")
        await pg.evaluate(FIX, [RADAR[0] - 100 * KLAT, RADAR[1], 12, 180, t, 5]); t += 1000
        on2 = await pg.evaluate("document.querySelector('#radBox').classList.contains('on')")
        await pg.evaluate(FIX, [base[0], base[1] + 300 * KLON, 12, 180, t, 5]); t += 1000
        on3 = await pg.evaluate("document.querySelector('#radBox').classList.contains('on')")
        check('sem rota: avisa radar à frente no rumo, some depois de passar e ignora rua paralela', on1 and not on2 and not on3, f'{on1} {on2} {on3}')

        # ---------- marcar radar e guardar no aparelho ----------
        await pg.evaluate("document.querySelector('#bSet').click()"); await pg.wait_for_timeout(200)
        check('ajustes: seção Radares com contagem', 'radares guardados' in await pg.text_content('#radInfo'))
        await pg.click('#bRadMark'); await pg.wait_for_timeout(200); await pg.fill('#askIn', '50'); await pg.click('#askOk'); await pg.wait_for_timeout(900)
        await pg.evaluate("document.querySelector('#dlgSet').close()")
        await pg.reload(); await pg.wait_for_timeout(1500)
        r = await pg.evaluate("({n:TN.radars.size,u:[...TN.radars.values()].filter(r=>r.user).map(r=>r.max)})")
        check('radares (baixados e marcados) continuam depois de recarregar (OPFS)', r['n'] == 2 and r['u'] == [50], str(r))
        await pg.click('[data-pane=paneMap]'); await pg.evaluate(f'TN.map.setView([{RADAR[0]},{RADAR[1]}],15,{{animate:false}})'); await pg.wait_for_timeout(800)
        check('radares aparecem no mapa', await pg.evaluate("document.querySelectorAll('.radmk').length") == 2)
        txt = await pg.evaluate("[...document.querySelectorAll('.radmk')].map(e=>e.textContent).sort().join(',')")
        check('marcador do radar mostra o limite', txt == '50,60', txt)

        # ---------- falha de rede: rota não sai, oferece Waze/Google Maps ----------
        MODE['valhalla'] = 'fail'
        await pg.click('#bNav'); await pg.wait_for_timeout(300)
        await pg.click('#navRecent [data-rc="0"]'); await pg.wait_for_timeout(1500)
        txt = await pg.text_content('#navRoutes')
        check('sem rota: mensagem e botões Waze/Google Maps', 'Não consegui calcular' in txt and await pg.evaluate("document.querySelectorAll('#navRoutes [data-ext]').length") == 2, txt[:100])
        await pg.click('#navRoutes [data-ext="gmaps"]')
        check('Google Maps com destino', 'google.com/maps/dir/?api=1&destination=' in await pg.evaluate('window.__open.slice(-1)[0]'))
        await pg.click('#dlgNav [data-close]')
        check('fechar sem ir limpa a prévia', await pg.evaluate('!TN.navPlan&&!TN.nav'))

        # ---------- tulipas de largada/chegada; altimetria redesenha ao girar ----------
        g = '<?xml version="1.0"?><gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>' + ''.join(f'<trkpt lat="{LAT0}" lon="{LON0 + i * 50 * KLON:.6f}"><ele>{800 + 50 * math.sin(i / 8):.1f}</ele></trkpt>' for i in range(60)) + '</trkseg></trk></gpx>'
        await pg.evaluate('(x)=>TN.loadGPX(x,"e.gpx")', g); await pg.wait_for_timeout(400)
        await pg.click('[data-pane=paneRb]'); await pg.wait_for_timeout(300)
        tu = await pg.evaluate("[...document.querySelectorAll('#rbList .rbn')].map(r=>r.querySelector('img.tu')?'img':'vazio')")
        check('Largada e Chegada com desenho (não mais quadrado vazio)', tu and tu[0] == 'img' and tu[-1] == 'img', str(tu))
        await pg.evaluate("document.querySelector('#bElev').click()"); await pg.wait_for_timeout(1500)
        w1 = await pg.evaluate("Math.round(document.querySelector('#elevDiv svg').getBoundingClientRect().width)")
        await pg.set_viewport_size({'width': 800, 'height': 720}); await pg.wait_for_timeout(1500)
        w2 = await pg.evaluate("(()=>{const s=document.querySelectorAll('#elevDiv svg');return [s.length?Math.round(s[0].getBoundingClientRect().width):0,document.querySelector('#elevDiv').clientWidth]})()")
        check('altimetria se redimensiona quando a tela muda', w1 > 900 and abs(w2[0] - w2[1]) < 60, f'{w1} -> {w2}')

        # ---------- celular: cartão de navegação cabe em retrato e deitado ----------
        await pg.evaluate("TN.navStart(TN.parseTrip(%s),{name:'Destino com um nome bem comprido para testar',lat:%f,lon:%f})" % (json.dumps(trip(PTS)), DEST[0], DEST[1]))
        await pg.evaluate(FIX, [PTS[3][0], PTS[3][1], 10, 90, t, 5]); t += 1000
        for vw, vh, nome in [(360, 780, 'retrato'), (740, 360, 'deitado')]:
            await pg.set_viewport_size({'width': vw, 'height': vh}); await pg.wait_for_timeout(700)
            r = await pg.evaluate("(()=>{const c=document.querySelector('#navCard'),v=document.querySelector('#view').getBoundingClientRect(),b=c.getBoundingClientRect();return {in:b.left>=v.left-1&&b.right<=v.right+1,h:Math.round(b.height),vh:Math.round(v.height),ov:c.scrollWidth>c.clientWidth+2}})()")
            check(f'cartão de navegação cabe no celular {nome} ({vw}×{vh})', r['in'] and not r['ov'] and r['h'] <= r['vh'] * 0.45, str(r))
            await pg.screenshot(path=f'/tmp/claude-0/-home-user/51ac65f6-457e-5d09-b14e-b860846fbcdb/scratchpad/png/nav_{nome}.png')

        check('sem erros de página', not errs, str(errs[:3]))
        await b.close()
    print('\nRESULTADO:', 'tudo certo' if not FAILS else 'FALHAS: ' + '; '.join(FAILS))
    sys.exit(1 if FAILS else 0)

asyncio.run(main())
