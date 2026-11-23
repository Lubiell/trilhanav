"""v2.2.1: partida do GPS no APK (relato do celular real: ficava em "GPS ---" com o GPS do aparelho ligado).
O plugin de GPS em segundo plano é simulado com os comportamentos do código dele: "Service not running." quando chamado antes de o
serviço ligar, "Location services disabled." (código NOT_AUTHORIZED) com a localização desligada, e silêncio total."""
import asyncio, sys
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html'
FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

def fake(mode, notif_hangs=False):
    return """
window.__gpsFallbackMs=2500;window.__adds=0;window.__cbs=[];window.__removed=[];
window.Capacitor={isNativePlatform:()=>true,getPlatform:()=>'android',registerPlugin:(n)=>({
  requestNotifications:()=>%s,
  addWatcher:async(o,cb)=>{const k=++__adds;__cbs.push(cb);const MODE='%s';
    if(MODE==='notready'&&k===1){setTimeout(()=>cb(null,{message:'Service not running.'}),50);return 'w'+k}
    if(MODE==='disabled'&&k<=2){setTimeout(()=>cb(null,{message:'Location services disabled.',code:'NOT_AUTHORIZED'}),50);return 'w'+k}
    if(MODE==='silent')return 'w'+k;
    setTimeout(()=>cb({latitude:-19.92,longitude:-43.94,accuracy:6,speed:0,bearing:null,altitude:800,time:Date.now()}),100);return 'w'+k},
  removeWatcher:async o=>{__removed.push(o.id)},
  addListener:()=>Promise.resolve({remove(){}}),speak:async()=>{},appInfo:async()=>({version:'2.2.1',code:20201})})};
""" % ('new Promise(()=>{})' if notif_hangs else 'Promise.resolve()', mode)

async def run(p, mode, notif_hangs=False, geo=None):
    b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
    ctx = await b.new_context(viewport={'width': 1280, 'height': 720}, permissions=['geolocation'] if geo else [], geolocation=geo)
    await ctx.add_init_script(fake(mode, notif_hangs))
    await ctx.add_init_script("localStorage.setItem('tn_updT',String(Date.now()))")
    await ctx.route('**/lib/capacitor.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=''))
    pg = await ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.goto(URL)
    return b, pg, errs

st = lambda pg: pg.evaluate("({txt:document.querySelector('#gpsTxt').textContent,adds:__adds,fix:!!(TN.st&&document.querySelector('#gpsDot').className.includes('ok')),removed:__removed.slice()})")

async def main():
    async with async_playwright() as p:
        b, pg, errs = await run(p, 'notready')
        await pg.wait_for_timeout(600)
        r1 = await st(pg)
        await pg.wait_for_timeout(2600)
        r2 = await st(pg)
        check('serviço ainda não pronto: mostra o motivo em vez de "GPS ---"', r1['txt'] == 'GPS: Service not running.', str(r1))
        check('… e tenta de novo sozinho até receber posição', r2['adds'] == 2 and r2['txt'] == 'GPS ±6 m' and r2['fix'] and r2['removed'] == ['w1'], str(r2))
        check('sem erros de página', not errs, str(errs[:2])); await b.close()

        b, pg, errs = await run(p, 'disabled')
        await pg.wait_for_timeout(600)
        r1 = await st(pg); t1 = await pg.text_content('#toast')
        await pg.wait_for_timeout(4500)
        r2 = await st(pg)
        check('localização do celular desligada: diz isso (não "sem permissão")', r1['txt'] == 'GPS desligado no celular' and 'Ligue a localização' in t1, f'{r1} {t1}')
        check('… e volta sozinho quando a localização é ligada', r2['adds'] == 3 and r2['txt'] == 'GPS ±6 m', str(r2))
        await b.close()

        b, pg, errs = await run(p, 'silent', geo={'latitude': -19.93, 'longitude': -43.95, 'accuracy': 12})
        await pg.wait_for_timeout(1500)
        r1 = await st(pg)
        await pg.wait_for_timeout(2500)
        r2 = await st(pg); t2 = await pg.text_content('#toast')
        check('serviço mudo: enquanto espera mostra "ligando"', r1['txt'] == 'GPS: ligando…', str(r1))
        check('… depois de 25 s (aqui 2,5 s) usa o GPS do WebView como reserva', r2['txt'] == 'GPS ±12 m' and 'usando o GPS do app' in t2, f'{r2} {t2}')
        await pg.evaluate("__cbs[0]({latitude:-19.92,longitude:-43.94,accuracy:5,speed:0,bearing:null,altitude:800,time:Date.now()})"); await pg.wait_for_timeout(300)
        r3 = await pg.evaluate("({txt:document.querySelector('#gpsTxt').textContent})")
        await pg.context.set_geolocation({'latitude': -19.95, 'longitude': -43.97, 'accuracy': 30}); await pg.wait_for_timeout(1500)
        r4 = await pg.evaluate("({txt:document.querySelector('#gpsTxt').textContent})")
        check('quando o serviço nativo volta, o reserva é largado (sem duas fontes de posição)', r3['txt'] == 'GPS ±5 m' and r4['txt'] == 'GPS ±5 m', f'{r3} {r4}')
        check('sem erros de página', not errs, str(errs[:2])); await b.close()

        b, pg, errs = await run(p, 'ok', notif_hangs=True)
        await pg.wait_for_timeout(3000)
        r1 = await st(pg)
        await pg.wait_for_timeout(7000)
        r2 = await st(pg)
        check('pedido de permissão de notificação que nunca responde não trava o GPS (no máx. 8 s)', r1['adds'] == 0 and r2['adds'] == 1 and r2['txt'] == 'GPS ±6 m', f'{r1} {r2}')
        await b.close()
    print('\nRESULTADO:', 'tudo certo' if not FAILS else 'FALHAS: ' + '; '.join(FAILS))
    sys.exit(1 if FAILS else 0)

asyncio.run(main())
