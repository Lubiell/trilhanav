"""v2.7: busca de endereço sem internet (nomes do mapa offline) e rota longa sem internet (zoom 14 nas pontas + rodovia nos zooms baixos).
Usa dev/testmap.pmtiles (gerado por make_testmap.py / fixtures.py): Vila Alegre (lon -44.30) e Pedra Azul (lon -43.70), ~62 km, ligadas só pela BR-999."""
import asyncio, sys
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html'
FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

STUB = "window.__spk=[];Object.defineProperty(window,'speechSynthesis',{value:{speak:u=>window.__spk.push(u.text),cancel(){},getVoices(){return []}},configurable:true});localStorage.setItem('tn_updT',String(Date.now()));"
ONPOS = '''([lat,lon,t])=>TN.onPos({timestamp:t,coords:{latitude:lat,longitude:lon,altitude:0,accuracy:5,speed:0,heading:null}})'''
VA, PA = (-20.0, -44.303), (-20.003, -43.703)

async def newpage(b):
    ctx = await b.new_context(viewport={'width': 1280, 'height': 720})
    await ctx.add_init_script(STUB)
    net = []
    async def route(r):
        u = r.request.url
        if u.startswith('http://localhost') or 'cdnjs.cloudflare.com' in u or 'fonts.g' in u: await r.continue_(); return
        net.append(u); await r.abort()   # sem internet de verdade
    await ctx.route('**/*', route)
    pg = await ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.goto(URL); await pg.wait_for_timeout(1300)
    return pg, errs, net

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        pg, errs, net = await newpage(b)

        # sem mapa offline e sem internet: a busca explica o que falta
        await pg.evaluate("document.querySelector('#bNav').click()"); await pg.wait_for_timeout(300)
        await pg.evaluate("document.querySelectorAll('#dlgAsk[open]').forEach(d=>d.close())")
        await pg.fill('#navQ', 'pedra azul'); await pg.press('#navQ', 'Enter'); await pg.wait_for_timeout(500)
        msg = await pg.text_content('#navRes')
        check('sem mapa e sem internet: a busca diz o que falta', 'mapa offline' in msg, msg)
        await pg.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")

        await pg.set_input_files('#offIn', 'testmap.pmtiles'); await pg.wait_for_timeout(2500)
        t = 1_000_000_000_000
        await pg.evaluate(ONPOS, [VA[0], VA[1], t]); await pg.evaluate(ONPOS, [VA[0], VA[1], t + 1000])

        # ---- busca offline ----
        r = await pg.evaluate("TN.offSearch('pedra azul')")
        check('cidade de outra parte do mapa (índice do zoom 10)', r and r[0]['name'] == 'Pedra Azul' and r[0]['sub'].startswith('Cidade'), str(r[:2]))
        r = await pg.evaluate("TN.offSearch('serra')")
        check('povoado no meio do caminho', any(x['name'] == 'Serra Velha' and x['sub'].startswith('Vila') for x in r), str(r))
        r = await pg.evaluate("TN.offSearch('rua flores')")
        check('rua com nome perto de você (zoom 14), palavras fora de ordem e sem acento', r and r[0]['name'] == 'Rua das Flores (VA)' and r[0]['sub'].startswith('Rua'), str(r[:2]))
        r = await pg.evaluate("TN.offSearch('posto')")
        check('lugar (posto) perto de você', r and r[0]['name'] == 'Posto Trevo' and r[0]['sub'].startswith('Posto'), str(r[:2]))
        r = await pg.evaluate("TN.offSearch('rosario')")
        check('sem acento acha "Rua do Rosário"', any(x['name'] == 'Rua do Rosário' for x in r), str(r[:3]))
        r = await pg.evaluate("TN.offSearch('hospital')")
        check('lugar a mais de 6 km (Hospital em Pedra Azul) não aparece na busca de perto', not any(x['name'] == 'Hospital São José' for x in r), str(r))
        r = await pg.evaluate("(async()=>{const d=await navigator.storage.getDirectory();await d.removeEntry('busca.json');TN.resetSrch();const [a,b]=await Promise.all([TN.offSearch('pedra'),TN.offSearch('serra')]);return [a[0]&&a[0].name,b[0]&&b[0].name]})()")
        check('duas buscas ao mesmo tempo montam o índice uma vez e as duas respondem', r == ['Pedra Azul', 'Serra Velha'], str(r))
        check('o índice de cidades ficou guardado no aparelho (busca.json)', await pg.evaluate("(async()=>{const d=await navigator.storage.getDirectory();const f=await (await d.getFileHandle('busca.json')).getFile();return JSON.parse(await f.text()).items.length})()") == 3)

        # pela tela "Ir para", sem aceitar o aviso de internet
        await pg.evaluate("document.querySelector('#bNav').click()"); await pg.wait_for_timeout(300)
        await pg.evaluate("document.querySelectorAll('#dlgAsk[open]').forEach(d=>d.close())")
        await pg.fill('#navQ', 'pedra'); await pg.press('#navQ', 'Enter'); await pg.wait_for_timeout(800)
        check('"Ir para" sem internet mostra o resultado do mapa offline', 'Pedra Azul' in await pg.text_content('#navRes'), await pg.text_content('#navRes'))

        # ---- rota longa offline (62 km): escolher o resultado já calcula ----
        await pg.evaluate("document.querySelector('#navRes [data-i=\"0\"]').click()"); await pg.wait_for_timeout(2500)
        plan = await pg.evaluate("TN.navPlan&&{off:TN.navPlan.routes[0].offline,len:TN.navPlan.routes[0].len,pts:TN.navPlan.routes[0].pts.map(p=>[p.lat,p.lon])}")
        check('rota de ~62 km calculada sem internet', plan and plan['off'] and 60000 <= plan['len'] <= 68000, str(plan and (plan['off'], round(plan['len']))))
        if plan:
            mid = [q for q in plan['pts'] if -44.05 < q[1] < -43.95]
            check('passa pela BR-999 no meio do caminho (curva a lat ~ -19.996)', mid and max(q[0] for q in mid) > -19.9975, str(mid[:3]))
            check('começa nas ruas de Vila Alegre e termina em Pedra Azul', abs(plan['pts'][0][1] - VA[1]) < 1e-6 and abs(plan['pts'][-1][1] - (-43.70)) < 0.01, str((plan['pts'][0], plan['pts'][-1])))
        r = await pg.evaluate("(async()=>{const t=performance.now();const x=await TN.offlineRouteTo({lat:-20.0,lon:-44.303},{lat:-20.0,lon:-44.0});return {ms:performance.now()-t,ok:!!x,len:x&&x.len}})()")
        check('rota até o povoado (30 km) também sai, rápido', r['ok'] and r['ms'] < 3000, str(r))
        check('nada foi pedido à internet', not [u for u in net if 'photon' in u or 'valhalla' in u], str(net[:3]))
        check('sem erros', not errs, str(errs))

        # ---- reabrir: o índice vem do aparelho, sem reler o mapa inteiro ----
        await pg.reload(); await pg.wait_for_timeout(2500)
        r = await pg.evaluate("(async()=>{const a=TN.srchIdx;const t=performance.now();const x=await TN.offSearch('pedra');return {antes:a,depois:!!TN.srchIdx,primeiro:x[0]&&x[0].name}})()")
        check('depois de reabrir o app a busca usa o índice guardado', r['antes'] is None and r['depois'] and r['primeiro'] == 'Pedra Azul', str(r))
        await b.close()
    print('\nRESULTADO:', 'tudo certo' if not FAILS else 'FALHOU ' + str(FAILS))
    sys.exit(1 if FAILS else 0)

asyncio.run(main())
