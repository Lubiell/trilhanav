"""v2.7.3: cidades na gramática da voz ("Trilha, ir para Guidoval"), radares e lombadas de uma região inteira de uma vez,
avisos marcados por voz (blitz, buraco, obra, lombada, perigo) e postos/lugares pelo mapa offline.
Usa dev/testmap.pmtiles (fixtures.py): Vila Alegre (lon -44.30) e Pedra Azul (lon -43.70), Posto Trevo em Vila Alegre e
Hospital São José em Pedra Azul."""
import asyncio, json, re, sys, urllib.parse
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html'
FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

STUB = "window.__spk=[];Object.defineProperty(window,'speechSynthesis',{value:{speak:u=>window.__spk.push(u.text),cancel(){},getVoices(){return []}},configurable:true});localStorage.setItem('tn_updT',String(Date.now()));"
ONPOS = '''([lat,lon,t,v,h])=>TN.onPos({timestamp:t,coords:{latitude:lat,longitude:lon,altitude:0,accuracy:5,speed:v||0,heading:h==null?null:h}})'''
VA, PA = (-20.0, -44.303), (-20.003, -43.703)
# vocabulário de teste do modelo de voz: sem "pedra" (como "guidoval" no modelo de verdade), mas com "pe" e "dra"
VOCAB = '\n'.join(['pe', 'dra', 'azul', 'vila', 'alegre', 'serra', 'velha', 'a', 'o', 'é'] + ['palavra%d' % i for i in range(200)])
LOMB = (-20.0, -44.2930)   # lombada na Rua Principal de Vila Alegre, a leste do ponto de partida
RAD = (-20.0005, -44.2900)

def overpass_elements(body):
    q = urllib.parse.unquote_plus(body.split('data=', 1)[1])
    m = re.search(r'\((-?[\d.]+),(-?[\d.]+),(-?[\d.]+),(-?[\d.]+)\)', q)
    s, w, n, e = map(float, m.groups())
    els = [{'type': 'node', 'id': 501, 'lat': RAD[0], 'lon': RAD[1], 'tags': {'highway': 'speed_camera', 'maxspeed': '60'}},
           {'type': 'node', 'id': 502, 'lat': LOMB[0], 'lon': LOMB[1], 'tags': {'traffic_calming': 'bump'}},
           {'type': 'node', 'id': 503, 'lat': -19.95, 'lon': -44.10, 'tags': {'hazard': 'curve'}},
           {'type': 'node', 'id': 504, 'lat': -19.95, 'lon': -44.11, 'tags': {'amenity': 'bench'}}]   # outra coisa: ignorada
    return [x for x in els if s <= x['lat'] < n and w <= x['lon'] < e], q

async def newpage(b, net):
    ctx = await b.new_context(viewport={'width': 1280, 'height': 720})
    await ctx.add_init_script(STUB + ("localStorage.setItem('tn_netOk','true');" if net else ''))
    calls = {'overpass': 0, 'queries': [], 'fail_next': 0}
    async def route(r):
        u = r.request.url
        if u.startswith('http://localhost'):
            if u.endswith('/lib/vosk-words.txt'):
                await r.fulfill(status=200, body=VOCAB, headers={'content-type': 'text/plain; charset=utf-8'}); return
            await r.continue_(); return
        if 'cdnjs.cloudflare.com' in u or 'fonts.g' in u: await r.continue_(); return
        if 'maps.mail.ru' in u and net:
            calls['overpass'] += 1
            if calls['fail_next'] > 0:
                calls['fail_next'] -= 1; await r.fulfill(status=504, body='<html>504 Gateway Time-out</html>'); return
            els, q = overpass_elements(r.request.post_data or 'data=')
            calls['queries'].append(q)
            await r.fulfill(status=200, body=json.dumps({'elements': els}), headers={'content-type': 'application/json', 'access-control-allow-origin': '*'}); return
        await r.abort()
    await ctx.route('**/*', route)
    pg = await ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.goto(URL); await pg.wait_for_timeout(1300)
    return pg, errs, calls

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        pg, errs, calls = await newpage(b, net=True)
        spk = lambda: pg.evaluate('window.__spk.slice()')
        async def said(n0): return (await spk())[n0:]

        # ---------- frases ----------
        cases = [('marcar blitz', 'mark', 'blitz'), ('marca buraco aqui', 'mark', 'buraco'), ('marcar quebra molas', 'mark', 'lombada'),
                 ('marcar obra', 'mark', 'obra'), ('marcar acidente', 'mark', 'perigo'), ('marcar polícia', 'mark', 'blitz'), ('marcar radar', 'radar', None),
                 ('apagar aviso', 'unmark', None), ('tira essa blitz', 'unmark', None), ('hospital mais perto', 'poi', None), ('onde tem farmácia', 'poi', None),
                 ('posto', 'fuel', None), ('ir para guido val', 'go', None)]
        got = await pg.evaluate("cs=>cs.map(t=>{const c=TN.parseCmd(t);return c&&[c.a,c.k&&!Array.isArray(c.k)?c.k:null]})", [c[0] for c in cases])
        bad = [(c[0], c[1:], g) for c, g in zip(cases, got) if not g or g[0] != c[1] or (c[2] and g[1] != c[2])]
        check('frases novas (marcar, apagar, lugares)', not bad, str(bad))

        # ---------- cidades na gramática ----------
        await pg.set_input_files('#offIn', 'testmap.pmtiles'); await pg.wait_for_timeout(2500)
        t = 1_000_000_000_000
        await pg.evaluate(ONPOS, [VA[0], VA[1], t, 0, None]); await pg.evaluate(ONPOS, [VA[0], VA[1], t + 1000, 0, None])
        r = await pg.evaluate("(async()=>{const r=await TN.placeGrammar(true);return {r,al:[...TN.PALIAS.entries()],w:TN.placeW}})()")
        al = dict(r['al'])
        check('nome fora do vocabulário vira pedaços conhecidos ("pedra azul" → "pe dra azul") e volta ao nome', al.get('pedraazul') == 'Pedra Azul' and 'pe' in r['w'] and 'dra' in r['w'] and 'pedra' not in r['w'], str(r))
        check('nomes que o modelo conhece entram inteiros', al.get('vilaalegre') == 'Vila Alegre' and al.get('serravelha') == 'Serra Velha', str(al))
        sg = await pg.evaluate("(()=>{const V=new Set(['a','ragu','ari','ara','gu','guido','val','mu','ria','é','u','bá']);return [TN.segWord('guidoval',V),TN.segWord('muriaé',V),TN.segWord('ubá',V),TN.segWord('araguari',V),TN.segWord('xyz',V)]})()")
        check('pedaços: Guidoval, Muriaé, Ubá; não começa com "a"/"o" soltos (somem depois do "para")', sg[0] == ['guido', 'val'] and sg[1] == ['mu', 'ria', 'é'] and sg[2] == ['u', 'bá'] and sg[3] == ['ara', 'gu', 'ari'] and sg[4] is None, str(sg))
        n0 = len(await spk())
        await pg.evaluate("TN.onHeard({text:'trilha ir para pe dra azul'})"); await pg.wait_for_timeout(5000)
        nv = await pg.evaluate("TN.nav&&{to:TN.nav.to.name,off:TN.nav.rt.offline,len:TN.nav.rt.len}")
        check('"Trilha, ir para Pedra Azul" (ouvido "pe dra azul") já calcula a rota a partir do GPS', nv and nv['to'] == 'Pedra Azul' and nv['off'] and nv['len'] > 55000, str(nv) + str((await said(n0))[-2:]))
        await pg.evaluate("TN.navStop()")

        c0 = calls['overpass']; fl = await pg.evaluate("TN.fuelFind().then(l=>l.map(f=>[f.name,!!f.off]))")
        check('posto com internet e mapa offline: usa o mapa primeiro (sem esperar a internet)', fl and fl[0] == ['Posto Trevo', True] and calls['overpass'] == c0, str((fl, calls['overpass'] - c0)))

        # ---------- radares e lombadas de uma região inteira ----------
        c0 = calls['overpass']; calls['fail_next'] = 1; await pg.evaluate('dlRetryMs=100')
        r = await pg.evaluate("TN.radBulk([-20.2,-44.5,-19.8,-43.5],1)")
        kinds = await pg.evaluate("(()=>{const c={};for(const r of TN.radars.values())c[r.k]=(c[r.k]||0)+1;return c})()")
        check('baixa a região em blocos (4 blocos de 1°) e guarda radar, lombada e perigo (o resto do OSM é ignorado)', r and r['blocks'] == 4 and r['fail'] == 0 and kinds == {'radar': 1, 'lombada': 1, 'perigo': 1}, str((r, kinds)))
        q = calls['queries'][c0] if len(calls['queries']) > c0 else ''
        check('a consulta pede radar, lombada e perigo', 'speed_camera' in q and 'traffic_calming' in q and 'hazard' in q, q[:200])
        check('bloco que deu 504 é pedido de novo e completa', calls['overpass'] - c0 >= 5, str(calls['overpass'] - c0))
        tiles = await pg.evaluate("Object.keys(TN.radTiles).length")
        check('os quadrados da região ficam marcados como baixados (64 de 0,25°)', tiles >= 64, str(tiles))
        c1 = calls['overpass']; r2 = await pg.evaluate("TN.radBulk([-20.2,-44.5,-19.8,-43.5],1)")
        check('baixar de novo não repete o que já está guardado', r2['done'] == 4 and calls['overpass'] == c1, str((r2, calls['overpass'] - c1)))
        info = await pg.text_content('#radInfo')
        check('Ajustes mostram radares, lombadas e avisos', 'radares guardados' in info and 'lombadas' in info and 'avisos' in info, info)

        # ---------- aviso de lombada ao se aproximar (indo para leste a 40 km/h) ----------
        async def drive(lon0, lon1, v_kmh, t):
            n = 8
            for i in range(n + 1):
                lo = lon0 + (lon1 - lon0) * i / n; t += 2000
                await pg.evaluate(ONPOS, [-20.0, lo, t, v_kmh / 3.6, 90])
            return t
        n0 = len(await spk()); t = await drive(-44.2990, -44.2945, 40, t + 5000)
        s = await said(n0)
        check('lombada à frente a 40 km/h: voz avisa', any(x.startswith('Lombada em') for x in s), str(s))
        lb = await pg.evaluate("document.querySelector('#radLim').textContent")
        check('placa mostra o símbolo da lombada', lb == '⌒', lb)
        n0 = len(await spk()); t = await drive(-44.2990, -44.2945, 12, t + 600000)
        check('devagar (12 km/h) a lombada não é avisada', not any(x.startswith('Lombada') for x in await said(n0)), str(await said(n0)))

        # ---------- marcar por voz ----------
        await pg.evaluate(ONPOS, [-20.0, -44.2800, t + 60000, 0, None])
        n0 = len(await spk()); await pg.evaluate("TN.runCmd(TN.parseCmd('marcar blitz'))")
        s = await said(n0)
        bz = await pg.evaluate("(()=>{const r=[...TN.radars.values()].find(r=>r.k==='blitz');return r&&{u:r.user,h:(r.exp-Date.now())/3600e3}})()")
        check('"marcar blitz" guarda uma blitz por 4 horas', s == ['Blitz marcada por 4 horas'] and bz and bz['u'] and 3.9 < bz['h'] <= 4, str((s, bz)))
        n0 = len(await spk()); await pg.evaluate("TN.runCmd(TN.parseCmd('marcar buraco'))")
        check('"marcar buraco"', (await said(n0)) == ['Buraco marcado'], str(await said(n0)))
        # aproximando da blitz (marcada em lon -44.28) vindo do oeste
        n0 = len(await spk()); t = await drive(-44.2850, -44.2815, 40, t + 120000)
        s = await said(n0)
        check('aviso da blitz marcada ao se aproximar', any(x.startswith('Blitz marcada em') for x in s), str(s))
        n0 = len(await spk()); await pg.evaluate("TN.runCmd(TN.parseCmd('apagar aviso'))")
        left = await pg.evaluate("[...TN.radars.values()].filter(r=>r.user).map(r=>r.k)")
        check('"apagar aviso" apaga o mais perto', len(left) == 1 and (await said(n0))[0].startswith('Aviso apagado'), str((left, await said(n0))))
        # blitz vencida não avisa e some ao reabrir
        await pg.evaluate("TN.runCmd(TN.parseCmd('marcar blitz'))")
        await pg.evaluate("[...TN.radars.values()].filter(r=>r.k==='blitz').forEach(r=>r.exp=Date.now()-1000)")
        n0 = len(await spk()); t = await drive(-44.2850, -44.2815, 40, t + 400000)
        check('blitz vencida não é avisada', not any(x.startswith('Blitz') for x in await said(n0)), str(await said(n0)))
        await pg.evaluate("TN.radMarkVoice('obra')"); await pg.wait_for_timeout(800)
        await pg.reload(); await pg.wait_for_timeout(2500)
        k2 = await pg.evaluate("(()=>{const c={};for(const r of TN.radars.values())c[r.k]=(c[r.k]||0)+1;return c})()")
        check('ao reabrir: tipos guardados (radar, lombada, perigo, buraco, obra) e a blitz vencida sumiu', k2 == {'radar': 1, 'lombada': 1, 'perigo': 1, 'buraco': 1, 'obra': 1}, str(k2))
        await pg.evaluate('''(async()=>{const d=await navigator.storage.getDirectory();const w=await (await d.getFileHandle('radares.json',{create:true})).createWritable();
          await w.write(JSON.stringify({v:1,tiles:{'-80_-178':Date.now()},pts:[['o900',-19.9,-44.2,40,null]]}));await w.close()})()''')
        await pg.reload(); await pg.wait_for_timeout(2500)
        r = await pg.evaluate("({t:Object.keys(TN.radTiles).length,p:[...TN.radars.values()].map(r=>[r.id,r.k,r.max])})")
        check('radares.json da v2.7.2: radar antigo vale; áreas marcadas só com radar são baixadas de novo', r['t'] == 0 and r['p'] == [['o900', 'radar', 40]], str(r))
        check('sem erros (com internet)', not errs, str(errs))
        await pg.context.close()

        # ---------- postos e lugares pelo mapa offline, sem internet nem aviso aceito ----------
        pg, errs, calls = await newpage(b, net=False)
        spk = lambda: pg.evaluate('window.__spk.slice()')
        async def said(n0): return (await spk())[n0:]
        await pg.set_input_files('#offIn', 'testmap.pmtiles'); await pg.wait_for_timeout(2500)
        t = 1_000_000_000_000
        await pg.evaluate(ONPOS, [VA[0], VA[1], t, 0, None]); await pg.evaluate(ONPOS, [VA[0], VA[1], t + 1000, 0, None])
        n0 = len(await spk()); await pg.evaluate("TN.runCmd(TN.parseCmd('posto'))"); await pg.wait_for_timeout(3000)
        s = await said(n0); nv = await pg.evaluate("TN.nav&&TN.nav.to.name")
        check('"posto" sem internet: o mais perto pelo mapa offline e a rota até ele', s and s[0].startswith('Posto mais perto: Posto Trevo') and nv == 'Posto Trevo', str((s, nv)))
        await pg.evaluate("TN.navStop()")
        await pg.evaluate("document.querySelector('#bFuel').click()"); await pg.wait_for_timeout(1500)
        fi = await pg.text_content('#fuelInfo')
        check('tela de postos sem internet lista pelo mapa offline', 'mapa offline' in fi and 'Posto Trevo' in await pg.text_content('#fuelList'), fi)
        await pg.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
        await pg.evaluate(ONPOS, [PA[0], PA[1], t + 5000, 0, None]); await pg.evaluate(ONPOS, [PA[0], PA[1], t + 6000, 0, None])
        n0 = len(await spk()); await pg.evaluate("TN.runCmd(TN.parseCmd('hospital mais perto'))"); await pg.wait_for_timeout(3000)
        s = await said(n0); nv = await pg.evaluate("TN.nav&&TN.nav.to.name")
        check('"hospital mais perto" pelo mapa offline', s and s[0].startswith('Hospital mais perto: Hospital São José') and nv == 'Hospital São José', str((s, nv)))
        await pg.evaluate("TN.navStop()")
        n0 = len(await spk()); await pg.evaluate("TN.runCmd(TN.parseCmd('ir para o hospital'))"); await pg.wait_for_timeout(3000)
        s = await said(n0); nv = await pg.evaluate("TN.nav&&TN.nav.to.name")
        check('"ir para o hospital" vai ao hospital mais perto (não procura um lugar chamado "hospital")', s and s[0].startswith('Hospital mais perto') and nv == 'Hospital São José', str((s, nv)))
        await pg.evaluate("TN.navStop()")
        await pg.evaluate(ONPOS, [VA[0], VA[1], t + 9000, 0, None]); await pg.evaluate(ONPOS, [VA[0], VA[1], t + 10000, 0, None])
        n0 = len(await spk()); await pg.evaluate("TN.runCmd(TN.parseCmd('me leva no posto'))"); await pg.wait_for_timeout(3000)
        s = await said(n0)
        check('"me leva no posto" vai ao posto mais perto', s and s[0].startswith('Posto mais perto: Posto Trevo'), str(s))
        n0 = len(await spk()); await pg.evaluate("TN.runCmd(TN.parseCmd('farmácia'))"); await pg.wait_for_timeout(2500)
        check('lugar que não existe perto: avisa', (await said(n0)) == ['Nenhum lugar desse tipo perto no mapa'], str(await said(n0)))
        check('nada foi pedido à internet', calls['overpass'] == 0)
        check('sem erros (sem internet)', not errs, str(errs))
        await b.close()
    print('\nRESULTADO:', 'tudo certo' if not FAILS else 'FALHOU ' + str(FAILS))
    sys.exit(1 if FAILS else 0)

asyncio.run(main())
