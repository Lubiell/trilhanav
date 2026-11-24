"""v2.7.6: botão "Sair do app" (grade Mais). Pergunta antes; Cancelar não faz nada; Sair guarda a trilha gravada em
Arquivos → Gravações, encerra a rota, para o assistente de voz e o GPS e chama o exitApp do nativo (que para os serviços e
encerra o processo; o lado Java só roda no celular). No navegador só avisa. Nativo simulado."""
import asyncio, sys
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html'
FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

FAKE = """
window.__calls=[];window.__ls={};localStorage.setItem('tn_updT',String(Date.now()));
window.__status={phone:true,contacts:true,mic:true,notifAccess:true,speech:true,installAllowed:true,sdk:34,voiceOn:true,notif:{connected:true}};
window.__emit=(ev,d)=>(window.__ls[ev]||[]).forEach(f=>f(d));
const rec=m=>async o=>{__calls.push([m,o||{}])};
window.Capacitor={isNativePlatform:()=>true,getPlatform:()=>'android',registerPlugin:(n)=>({
  addWatcher:async()=>{__calls.push(['addWatcher',{}]);return 'w1'},removeWatcher:rec('removeWatcher'),requestNotifications:async()=>{},speak:rec('speak'),
  addListener:(ev,cb)=>{(__ls[ev]=__ls[ev]||[]).push(cb);return Promise.resolve({remove(){}})},
  phoneStatus:async()=>__status,listContacts:async()=>({list:[]}),
  voiceStart:async o=>{__calls.push(['voiceStart',o]);setTimeout(()=>__emit('voice',{state:'on'}),50)},voiceStop:rec('voiceStop'),voiceBt:rec('voiceBt'),
  exitApp:rec('exitApp'),appInfo:async()=>({version:'2.7.6',code:20706})})};
"""
ONPOS = '''([lat,lon,t,v])=>TN.onPos({timestamp:t,coords:{latitude:lat,longitude:lon,altitude:800,accuracy:5,speed:v,heading:90}})'''
LAT0, LON0 = -19.92, -43.94

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        ctx = await b.new_context(viewport={'width': 1280, 'height': 720})
        await ctx.add_init_script(FAKE)
        async def route(r):
            u = r.request.url
            if u.endswith('/lib/capacitor.js'): await r.fulfill(status=200, content_type='application/javascript', body=''); return
            if u.startswith('http://localhost') or 'cdnjs.cloudflare.com' in u or 'fonts.g' in u: await r.continue_(); return
            await r.abort()
        await ctx.route('**/*', route)
        pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(URL); await pg.wait_for_timeout(2200)
        names = lambda: pg.evaluate('__calls.map(c=>c[0])')

        # ---------- botão na grade Mais ----------
        await pg.click('#bMore'); await pg.wait_for_timeout(200)
        r = await pg.evaluate("(()=>{const b=document.querySelector('#moreGrid #bExit');return b&&{t:b.textContent.trim(),ic:!!document.querySelector(b.querySelector('use').getAttribute('href'))}})()")
        check('"Sair do app" na grade Mais, com ícone', r == {'t': 'Sair do app', 'ic': True}, str(r))

        # gravando uma trilha e com rota em andamento
        await pg.evaluate("document.querySelector('#dlgMore').close()")
        await pg.evaluate("document.querySelector('#bRec').click()")
        t = 1_000_000_000_000
        for i in range(6):
            await pg.evaluate(ONPOS, [LAT0, LON0 + i * 0.0003, t, 8]); t += 4000
        await pg.evaluate("(()=>{const rt=TN.offNavRoute(TN.mkRoute([{lat:%f,lon:%f},{lat:%f,lon:%f}]),true);rt.straight=true;TN.navStart(rt,{name:'Destino',lat:%f,lon:%f},null)})()" % (LAT0, LON0, LAT0, LON0 + 0.05, LAT0, LON0 + 0.05))
        await pg.wait_for_timeout(300)
        check('com rota em andamento', await pg.evaluate('!!TN.nav'))

        # ---------- pergunta antes; Cancelar não faz nada ----------
        n0 = len(await names())
        await pg.evaluate("document.querySelector('#bExit').click()"); await pg.wait_for_timeout(300)
        r = await pg.evaluate("({open:document.querySelector('#dlgAsk').open,t:document.querySelector('#askT').textContent,m:document.querySelector('#askMsg').textContent,ok:document.querySelector('#askOk').textContent})")
        check('pergunta antes de sair (cita a rota, a trilha gravada e o que para)', r['open'] and r['t'] == 'Sair do TrilhaNav?' and 'rota' in r['m'] and 'pontos' in r['m'] and 'Gravações' in r['m'] and 'GPS' in r['m'] and r['ok'] == 'Sair', str(r))
        await pg.click('#askNo'); await pg.wait_for_timeout(300)
        check('Cancelar: nada para e o app continua', (await names())[n0:] == [] and await pg.evaluate('!!TN.nav'), str((await names())[n0:]))

        # ---------- Sair ----------
        await pg.evaluate("document.querySelector('#bExit').click()"); await pg.wait_for_timeout(300)
        await pg.click('#askOk'); await pg.wait_for_timeout(800)
        seq = [x for x in (await names())[n0:] if x in ('voiceStop', 'removeWatcher', 'exitApp')]
        check('Sair: para o assistente de voz e o GPS e só então fecha o app', seq == ['voiceStop', 'removeWatcher', 'exitApp'], str(seq))
        check('Sair: a rota é encerrada', not await pg.evaluate('!!TN.nav'))
        g = await pg.evaluate('''(async()=>{const d=await navigator.storage.getDirectory();const g=await (await d.getDirectoryHandle('gpx')).getDirectoryHandle('Gravações');
          const out=[];for await (const [n,h] of g.entries()){if(n.endsWith('.gpx'))out.push([n,(await (await h.getFile()).text()).split('<trkpt').length-1])}return out})()''')
        check('Sair: a trilha gravada fica em Arquivos → Gravações (GPX com os pontos)', len(g) == 1 and g[0][0].startswith('trilhanav_') and g[0][1] >= 4, str(g))
        check('sem erros (APK)', not errs, str(errs[:3]))
        await ctx.close()

        # ---------- sem gravação nem rota: a pergunta é curta e não grava arquivo ----------
        ctx = await b.new_context(viewport={'width': 1280, 'height': 720})
        await ctx.add_init_script(FAKE); await ctx.route('**/*', route)
        pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(URL); await pg.wait_for_timeout(1800)
        await pg.evaluate("document.querySelector('#bExit').click()"); await pg.wait_for_timeout(300)
        m = await pg.text_content('#askMsg')
        check('sem rota nem gravação: a pergunta fala só do que para', 'rota' not in m and 'pontos' not in m and 'GPS' in m, m)
        await pg.click('#askOk'); await pg.wait_for_timeout(600)
        g = await pg.evaluate('''(async()=>{try{const d=await navigator.storage.getDirectory();const g=await (await d.getDirectoryHandle('gpx')).getDirectoryHandle('Gravações');
          let n=0;for await (const [k] of g.entries())if(k.endsWith('.gpx'))n++;return n}catch(e){return 0}})()''')
        check('… e chama o exitApp sem criar gravação vazia', 'exitApp' in await names() and g == 0, str(g))
        check('sem erros (APK, sem gravação)', not errs, str(errs[:3]))
        await ctx.close()

        # ---------- no navegador (sem APK): só avisa ----------
        pg = await b.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(URL); await pg.wait_for_timeout(1000)
        await pg.evaluate("document.querySelector('#bExit').click()"); await pg.wait_for_timeout(200)
        check('no navegador: avisa para fechar a aba, sem perguntar', 'feche a aba' in await pg.text_content('#toast') and not await pg.evaluate("document.querySelector('#dlgAsk').open"))
        check('sem erros (navegador)', not errs, str(errs[:3]))
        await b.close()
    print('\nRESULTADO:', 'tudo certo' if not FAILS else 'FALHOU ' + str(FAILS))
    sys.exit(1 if FAILS else 0)

asyncio.run(main())
