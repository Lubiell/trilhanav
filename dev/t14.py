"""Caça a erros (v2.0.1), só o que vale sem as funções de rali: 1ª posição imprecisa, exportar no APK, celular deitado, offline real."""
import asyncio, sys, math, base64
from playwright.async_api import async_playwright

FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

URL = 'http://localhost:8765/index.html'
K = 0.0095699
M_LAT = 111194.9; M_LON = M_LAT * math.cos(math.radians(20))
T0 = 1_000_000_000_000

POS = '([lat,lon,t,acc,spd])=>TN.onPos({timestamp:t,coords:{latitude:lat,longitude:lon,altitude:0,accuracy:acc,speed:spd,heading:null}})'
RIDE = '''([t0,K,n])=>{for(let i=0;i<=n;i++)TN.onPos({timestamp:t0+i*2000,coords:{latitude:-20,longitude:-44+i*0.03*K,altitude:0,accuracy:5,speed:15,heading:90}})}'''
SPEECH = "window.__spk=[];Object.defineProperty(window,'speechSynthesis',{value:{speak:u=>window.__spk.push(u.text),cancel(){},getVoices(){return []}},configurable:true});"
FAKE_CAP = """window.__calls=[];window.Capacitor={isNativePlatform:()=>true,registerPlugin:(n)=>({addWatcher:async()=>'w1',removeWatcher:async()=>{},requestNotifications:async()=>{},speak:async()=>{},mediaKey:async()=>{},openApp:async()=>{},
  shareFile:async o=>{__calls.push(o)}})};"""

async def page(b, init=None):
    ctx = await b.new_context(viewport={'width': 1600, 'height': 720})
    if init: await ctx.add_init_script(init)
    pg = await ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.goto(URL); await pg.wait_for_timeout(1200)
    return pg, errs

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')

        # 4) primeira posição imprecisa não soma distância
        pg, errs = await page(b)
        await pg.evaluate(POS, [-20.0, -44.0, T0, 800, None])
        await pg.evaluate(POS, [-20.0, -44.0 + 0.6 * K, T0 + 12000, 6, 0]); await pg.evaluate(POS, [-20.0, -44.0 + 0.6 * K, T0 + 13000, 6, 0])
        check('posição de rede (±800 m) seguida de GPS bom a 600 m: km rodados continuam 0 (antes: 0,60 km)', await pg.evaluate('TN.fuelKm') == 0, str(await pg.evaluate('TN.fuelKm')))
        await pg.evaluate(POS, [-20.0, -44.0 + 0.7 * K, T0 + 23000, 6, 10])
        check('depois disso os km contam normalmente (100 m)', abs(await pg.evaluate('TN.fuelKm') - 0.1) < 0.005, str(await pg.evaluate('TN.fuelKm')))
        await pg.context.close()

        # 10) no APK, exportar entrega o arquivo pela tela de compartilhar (o WebView não baixa)
        pg, errs = await page(b, FAKE_CAP)
        await pg.evaluate("()=>{window.__a=0;const o=HTMLAnchorElement.prototype.click;HTMLAnchorElement.prototype.click=function(){if(this.download)window.__a++;return o.call(this)}}")
        await pg.click('#bRec'); await pg.evaluate(RIDE, [T0, K, 10])
        await pg.evaluate("document.querySelector('#bSet').click()"); await pg.click('#bExport'); await pg.wait_for_timeout(600)
        calls = await pg.evaluate('__calls')
        txt = base64.b64decode(calls[0]['data']).decode() if calls else ''
        check('exportar chama shareFile com nome .gpx e o conteúdo em base64', len(calls) == 1 and calls[0]['name'].endswith('.gpx') and calls[0]['mime'] == 'application/gpx+xml' and '<trkpt' in txt and txt.startswith('<?xml'), str(calls and {k: str(v)[:40] for k, v in calls[0].items()}))
        await pg.click('#bBackup'); await pg.wait_for_timeout(400)
        calls = await pg.evaluate('__calls')
        check('backup de ajustes também vai pela tela de compartilhar; nenhum <a download> é usado', len(calls) == 2 and calls[1]['name'] == 'trilhanav_ajustes.json' and await pg.evaluate('window.__a') == 0, str(len(calls)))
        check('sem erros (APK)', not errs, str(errs))
        await pg.context.close()
        pg, errs = await page(b)
        await pg.evaluate("()=>{window.__a=0;const o=HTMLAnchorElement.prototype.click;HTMLAnchorElement.prototype.click=function(){if(this.download)window.__a++;return o.call(this)}}")
        await pg.evaluate("document.querySelector('#bSet').click()"); await pg.click('#bBackup'); await pg.wait_for_timeout(300)
        check('no navegador o download continua pelo <a download>', await pg.evaluate('window.__a') == 1)
        await pg.context.close()

        # 12) celular deitado (guidão): os mostradores cabem sem rolar
        for w, h in ((740, 360), (915, 412), (568, 320)):
            ctx = await b.new_context(viewport={'width': w, 'height': h}, has_touch=True, is_mobile=True); pg = await ctx.new_page()
            await pg.goto(URL); await pg.wait_for_timeout(1000)
            await pg.evaluate("()=>{const t=Date.now();for(let i=0;i<2;i++)TN.onPos({timestamp:t+i*1000,coords:{latitude:-20,longitude:-44+i*0.0003,altitude:0,accuracy:5,speed:33,heading:271}})}")
            r = await pg.evaluate("""()=>{const s=document.querySelector('#side'),sb=s.getBoundingClientRect();return {rola:s.scrollHeight-s.clientHeight,
              fora:['#cap','#speed'].filter(q=>{const r=document.querySelector(q).getBoundingClientRect();return r.bottom>sb.bottom+1||r.top<sb.top-1}),
              estouro:['#cap','#speed'].filter(q=>{const e=document.querySelector(q);return e.scrollWidth>e.clientWidth})}}""")
            check(f'{w}x{h}: CAP e VELOCIDADE visíveis sem rolar (antes: velocidade fora da tela)', r['rola'] <= 0 and not r['fora'] and not r['estouro'], str(r))
            await ctx.close()

        # 11) offline de verdade: sem rede e com o cache HTTP limpo, só resta o que o service worker guardou
        ctx = await b.new_context(viewport={'width': 1600, 'height': 720}); pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(URL); await pg.wait_for_timeout(800)
        await pg.evaluate("(async()=>{await navigator.serviceWorker.register('sw.js');await navigator.serviceWorker.ready})()")
        await pg.wait_for_timeout(5000); await pg.reload(); await pg.wait_for_timeout(3000)
        await pg.evaluate("fetch('NOTICE.md').then(r=>r.text())"); await pg.wait_for_timeout(1500)
        c = await pg.evaluate('''(async()=>{const v=(await caches.keys()).find(k=>/^trilhanav-v/.test(k));const us=(await (await caches.open(v)).keys()).map(r=>r.url);return {v,notice:us.some(u=>/NOTICE/.test(u)),css:us.filter(u=>/fonts\\.googleapis/.test(u)).length,woff:us.filter(u=>/fonts\\.gstatic/.test(u)).length}})()''')
        check('o service worker guarda em tempo de uso (arquivo fora da lista fixa e as fontes)', c['notice'] and c['css'] >= 1 and c['woff'] >= 2, str(c))
        await ctx.set_offline(True)
        cdp = await ctx.new_cdp_session(pg); await cdp.send('Network.clearBrowserCache')
        await pg.reload(); await pg.wait_for_timeout(3500)
        r = await pg.evaluate('''()=>{const w=f=>{const s=document.createElement('span');s.style.cssText='font:900 40px '+f+';position:absolute;visibility:hidden';s.textContent='0123456789';document.body.appendChild(s);const x=s.offsetWidth;s.remove();return x};
          return {L:typeof L,tn:typeof TN,orb:[...document.fonts].some(f=>/Orbitron/.test(f.family)&&f.status==='loaded'),wOrb:w('Orbitron,monospace'),wMono:w('monospace')}}''')
        check('sem internet o app abre', r['L'] == 'object' and r['tn'] == 'object', str(r))
        check('sem internet as fontes continuam (antes: os números caíam para a fonte padrão)', r['orb'] and r['wOrb'] != r['wMono'], str(r))
        miss = await pg.evaluate("fetch('nao-existe.js').then(r=>r.status+' '+(r.headers.get('content-type')||'')).catch(e=>'falhou')")
        check('arquivo que não está no cache falha de verdade, em vez de vir o index.html no lugar', miss == 'falhou', miss)
        check('sem erros (offline)', not errs, str(errs))
        await b.close()
    print('\nRESULTADO:', 'FALHOU ' + str(FAILS) if FAILS else 'tudo certo')
    sys.exit(1 if FAILS else 0)
asyncio.run(main())
