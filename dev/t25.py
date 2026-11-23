"""v2.7.1: download do mapa num Android em que reler o arquivo logo depois de gravar falha com
NotReadableError ("An operation that depends on state cached in an interface object was made but the state had changed
since it was read from disk"), como no celular do dono (2.6.3). Usa as fixtures de dl/ (fixtures.py)."""
import asyncio, sys
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html'
BASE = 'https://raw.githubusercontent.com/Lubiell/trilhanav/mapas/mg/'
FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

# File.arrayBuffer (reler o arquivo inteiro) sempre falha; File.slice(...).arrayBuffer falha nas primeiras N leituras
STALE = """(()=>{const err=()=>new DOMException('An operation that depends on state cached in an interface object was made but the state had changed since it was read from disk.','NotReadableError');
  window.__staleSlices=0;window.__staleWhole=0;
  const ab=File.prototype.arrayBuffer;File.prototype.arrayBuffer=function(){window.__staleWhole++;return Promise.reject(err())};
  const sl=File.prototype.slice;File.prototype.slice=function(...a){const b=sl.apply(this,a);if(window.__staleLeft>0){window.__staleLeft--;window.__staleSlices++;b.arrayBuffer=()=>Promise.reject(err())}return b};
  window.__staleLeft=0})();"""

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        ctx = await b.new_context(viewport={'width': 1280, 'height': 720})
        await ctx.add_init_script(STALE + "localStorage.setItem('tn_updT',String(Date.now()));")
        pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        async def handler(route):
            name = route.request.url.split('/')[-1]
            await route.fulfill(status=200, body=open('dl/' + name, 'rb').read(), headers={'access-control-allow-origin': '*', 'content-type': 'application/octet-stream'})
        await pg.route(BASE + '*', handler)
        await pg.goto(URL); await pg.wait_for_timeout(1500)
        await pg.evaluate('dlRetryMs=100')
        await pg.evaluate("window.__staleLeft=3")   # as 3 primeiras leituras do mapa também falham
        await pg.evaluate('downloadMap()')
        for _ in range(40):
            txt = await pg.text_content('#offInfo')
            if txt.startswith('Instalado') or 'interrompido' in txt: break
            await pg.wait_for_timeout(250)
        txt = await pg.text_content('#offInfo')
        check('download termina mesmo com o arquivo "mudado desde a leitura" (conferência nos bytes que chegaram)', txt.startswith('Instalado (Teste)'), txt)
        r = await pg.evaluate("({whole:window.__staleWhole,slices:window.__staleSlices,left:window.__staleLeft})")
        check('a conferência não relê o arquivo gravado', r['whole'] == 0, str(r))
        check('as leituras do mapa que falharam foram refeitas com o arquivo novo', r['slices'] == 3 and r['left'] == 0, str(r))
        ok = await pg.evaluate("(async()=>{const h=await TN.offPM.getHeader();const n=2**14,x=Math.floor((-44+180)/360*n),y=Math.floor((1-Math.asinh(Math.tan(-20.005*Math.PI/180))/Math.PI)/2*n);const t=await TN.offPM.getZxy(14,x,y).catch(e=>String(e));return {z:h.maxZoom,t:t&&t.data?t.data.byteLength:t}})()")
        check('o mapa lê os tiles depois disso', ok['z'] == 14 and isinstance(ok['t'], int) and ok['t'] > 0, str(ok))
        check('sem erros', not errs, str(errs))
        await b.close()
    print('\nRESULTADO:', 'tudo certo' if not FAILS else 'FALHOU ' + str(FAILS))
    sys.exit(1 if FAILS else 0)

asyncio.run(main())
