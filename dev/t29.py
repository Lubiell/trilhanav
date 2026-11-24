"""v2.7.7: mapa offline e radares guardados no aparelho (o dono: "download dos mapas, radares e lombada não estão sendo salvos").
Simula um Android em que a leitura do OPFS falha (NotReadableError, como no celular do dono na 2.7.1) ou a gravação falha.
Antes: radares.json ilegível ao abrir → lista vazia → a 1ª gravação apagava MG inteiro; manifest.json ilegível → "nenhum mapa".
Agora: nova tentativa, nunca grava por cima do que não leu, erro na tela e Ajustes → Armazenamento. Usa dev/dl (fixtures.py)."""
import asyncio, json, sys
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html'
MAPS = 'https://raw.githubusercontent.com/Lubiell/trilhanav/mapas/mg/'
FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

# falhas de leitura/gravação por nome de arquivo, controladas por sessionStorage (valem ao recarregar) e por window.__fail/__failW
STUB = """localStorage.setItem('tn_updT',String(Date.now()));localStorage.setItem('tn_netOk','true');
window.__fail=JSON.parse(sessionStorage.__fail||'{}');window.__failW=JSON.parse(sessionStorage.__failW||'{}');window.__reads={};
const _gf=FileSystemFileHandle.prototype.getFile,_cw=FileSystemFileHandle.prototype.createWritable;
FileSystemFileHandle.prototype.getFile=function(){const n=this.name;__reads[n]=(__reads[n]||0)+1;
  if(__fail[n]>0){__fail[n]--;return Promise.reject(new DOMException('An operation that depends on state cached in an interface object was made but the state had changed since it was read from disk.','NotReadableError'))}
  return _gf.call(this)};
FileSystemFileHandle.prototype.createWritable=function(o){const n=this.name;if(__failW[n]>0){__failW[n]--;return Promise.reject(new DOMException('cota cheia','QuotaExceededError'))}return _cw.call(this,o)};
"""
RADS = [['o%d' % (i + 1), -19.5 + (i % 50) * 0.002, -44.5 + (i // 50) * 0.002, 60, None, 'radar' if i % 3 else 'lombada', None] for i in range(500)]
READ_FILE = '''(async()=>{const d=await navigator.storage.getDirectory();const h=await d.getFileHandle('radares.json');
  const f=await FileSystemFileHandle.prototype.getFile.call(h);return JSON.parse(await f.text()).pts.length})()'''

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        ctx = await b.new_context(viewport={'width': 1280, 'height': 720})
        await ctx.add_init_script(STUB)
        state = {'over': 0}
        async def route(r):
            u = r.request.url
            if u.startswith(MAPS):
                await r.fulfill(status=200, body=open('dl/' + u.split('/')[-1], 'rb').read(), headers={'access-control-allow-origin': '*', 'content-type': 'application/octet-stream'}); return
            if 'maps.mail.ru' in u:
                state['over'] += 1
                el = {'type': 'node', 'id': 900000 + state['over'], 'lat': -19.9, 'lon': -43.9, 'tags': {'highway': 'speed_camera', 'maxspeed': '60'}}
                await r.fulfill(status=200, body=json.dumps({'elements': [el]}), headers={'content-type': 'application/json', 'access-control-allow-origin': '*'}); return
            if u.startswith('http://localhost') or 'cdnjs.cloudflare.com' in u or 'fonts.g' in u: await r.continue_(); return
            await r.abort()
        await ctx.route('**/*', route)
        pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        async def reload(fail=None, failW=None):
            await pg.evaluate("([a,b])=>{sessionStorage.__fail=JSON.stringify(a||{});sessionStorage.__failW=JSON.stringify(b||{})}", [fail, failW])
            await pg.reload(); await pg.wait_for_timeout(1800); await pg.evaluate('dlRetryMs=100')
        await pg.goto(URL); await pg.wait_for_timeout(1500)

        # ---------- radares guardados (500, como depois de baixar uma região) ----------
        await pg.evaluate('''(pts)=>(async()=>{const d=await navigator.storage.getDirectory();const w=await (await d.getFileHandle('radares.json',{create:true})).createWritable();
          await w.write(JSON.stringify({v:2,tiles:{'-80_-178':Date.now()},pts}));await w.close()})()''', RADS)
        await reload()
        check('radares guardados voltam ao abrir', await pg.evaluate('TN.radars.size') == 500 and await pg.evaluate('TN.radLoaded'))

        # ---------- leitura falha 2 vezes ao abrir: a 3ª tentativa lê ----------
        await reload({'radares.json': 2})
        check('leitura falhou 2 vezes ao abrir: tenta de novo e carrega os 500', await pg.evaluate('TN.radars.size') == 500 and await pg.evaluate('TN.radLoaded'), str(await pg.evaluate('TN.radars.size')))

        # ---------- leitura sempre falha: um radar novo chega e NÃO pode apagar os 500 guardados ----------
        await reload({'radares.json': 999})
        check('leitura sempre falha: ainda não leu o arquivo', not await pg.evaluate('TN.radLoaded') and await pg.evaluate('TN.radars.size') == 0)
        r = await pg.evaluate('TN.radBulk([-20,-44,-19.75,-43.75],0.25)')
        for _ in range(20):
            t = await pg.text_content('#toast')
            if 'Não consegui ler' in t: break
            await pg.wait_for_timeout(300)
        await pg.evaluate('window.__fail={}')
        n = await pg.evaluate(READ_FILE)
        check('radar novo com o arquivo ilegível: não grava por cima (os 500 continuam no aparelho)', n == 500, 'pontos no arquivo: %s' % n)
        check('… e avisa que não leu os radares guardados', 'Não consegui ler os radares guardados' in t, t)
        for _ in range(30):   # nova tentativa de leitura (a cada 5 s), agora sem falha
            if await pg.evaluate('TN.radLoaded'): break
            await pg.wait_for_timeout(500)
        check('quando a leitura volta: junta os 500 guardados com o novo', await pg.evaluate('TN.radLoaded') and await pg.evaluate('TN.radars.size') == 501, str(await pg.evaluate('TN.radars.size')))
        await pg.evaluate('TN.radSave()'); await pg.evaluate('TN.radFlush()')
        check('"gravar agora" (usado no Sair do app) grava sem esperar: 501 no arquivo', await pg.evaluate(READ_FILE) == 501)

        # ---------- gravação falha: avisa ----------
        await pg.evaluate("window.__failW={'radares.json':5}")
        await pg.evaluate('TN.radSave()'); await pg.wait_for_timeout(900)
        t = await pg.text_content('#toast')
        check('gravação falhou: avisa na tela (antes: calado)', 'Não consegui guardar os radares' in t and 'cota cheia' in t, t)
        check('… e o erro fica para o diagnóstico', 'gravar os radares' in (await pg.evaluate('TN.stoErr.radaresW||""')))
        await pg.evaluate('window.__failW={}')

        # ---------- mapa: baixa, e o manifest falha ao ler ao abrir ----------
        await pg.evaluate('downloadMap()'); await pg.wait_for_timeout(3000)
        check('mapa baixado', (await pg.text_content('#offInfo')).startswith('Instalado'), await pg.text_content('#offInfo'))
        await reload({'manifest.json': 2})
        check('manifest do mapa falhou 2 vezes ao abrir: tenta de novo e o mapa abre', (await pg.text_content('#offInfo')).startswith('Instalado') and await pg.evaluate('!!TN.offPM'), await pg.text_content('#offInfo'))
        await reload({'manifest.json': 999})
        for _ in range(20):
            oi = await pg.text_content('#offInfo')
            if 'está no aparelho' in oi: break
            await pg.wait_for_timeout(300)
        check('manifest sempre ilegível: diz que o mapa está no aparelho e não manda apagar (antes: "nenhum mapa")', 'está no aparelho' in oi and 'não apague' in oi, oi)
        await pg.evaluate('window.__fail={}')
        for _ in range(20):
            if await pg.evaluate('!!TN.offPM'): break
            await pg.wait_for_timeout(500)
        check('… e abre sozinho quando a leitura volta', (await pg.text_content('#offInfo')).startswith('Instalado') and await pg.evaluate('!!TN.offPM'), await pg.text_content('#offInfo'))

        # ---------- Ajustes → Armazenamento ----------
        await pg.evaluate("document.querySelector('#bSet').click()"); await pg.wait_for_timeout(1200)
        si = await pg.text_content('#stoInfo')
        check('mapa aberto: o erro antigo de leitura sai do diagnóstico', 'Erro (mapa)' not in si, si)
        check('Armazenamento: permanente?, espaço, mapa (partes), radares (arquivo e quantos) e gravações', 'permanente' in si and 'Espaço do app' in si and 'Mapa offline: 3 de 3 partes' in si and 'completo' in si
              and 'Radares: arquivo de' in si and 'radares/avisos' in si and 'Gravações' in si, si)
        await pg.evaluate("document.querySelector('#dlgSet').close()")
        await reload({'manifest.json': 999}); await pg.wait_for_timeout(1500)
        await pg.evaluate("window.__fail={'manifest.json':999}")
        await pg.evaluate("document.querySelector('#bSet').click()")
        for _ in range(20):
            si = await pg.text_content('#stoInfo')
            if 'Mapa offline' in si: break
            await pg.wait_for_timeout(300)
        check('Armazenamento mostra o erro de leitura do mapa (e que os arquivos estão lá)', 'Erro (mapa)' in si and 'NotReadableError' in si and '4 arquivo(s) do download no aparelho' in si, si)
        check('sem erros de página', not errs, str(errs[:3]))
        await b.close()
    print('\nRESULTADO:', 'tudo certo' if not FAILS else 'FALHOU ' + str(FAILS))
    sys.exit(1 if FAILS else 0)

asyncio.run(main())
