"""v2.7.8, a pedido do dono:
- "não abaixar a música do Spotify quando o app estiver funcionando; sobrepor só nas notificações do app": o microfone do capacete (SCO,
  que leva a música junto para o canal de ligação) vem desligado, também para quem já tinha (migração única); ligar de novo fica valendo.
- "não está aceitando baixar os mapas" (na 2.7.7: "não consegui ler o mapa que já está no aparelho"): manifest.json vazio/danificado não
  bloqueia mais; as partes são conferidas pelo SHA-256 e só a ruim baixa de novo.
- "o app tem que baixar sozinho os dados necessários para rodar tudo offline": mapa de MG sozinho no Wi-Fi (nos dados móveis espera o Wi-Fi),
  radares e lombadas de MG sozinhos com internet; no computador (sem tipo de conexão) nada começa sozinho.
- "outros arquivos externos… escolho e nada acontece": erro ao abrir um GPX agora aparece na tela.
Usa dev/dl (fixtures.py)."""
import asyncio, json, sys, os, tempfile
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html'
MAPS = 'https://raw.githubusercontent.com/Lubiell/trilhanav/mapas/mg/'
FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

BASE = "localStorage.setItem('tn_updT',String(Date.now()));localStorage.setItem('tn_netOk','true');"
def conn(t):   # navigator.connection de um celular (no computador o type não existe)
    return "Object.defineProperty(navigator,'connection',{configurable:true,get:()=>({type:%s,addEventListener(){},removeEventListener(){}})});" % json.dumps(t)

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')

        async def ctx_for(init):
            ctx = await b.new_context(viewport={'width': 1280, 'height': 720})
            await ctx.add_init_script(BASE + init)
            st = {'man': 0, 'parts': [], 'over': 0}
            async def route(r):
                u = r.request.url
                if u.startswith(MAPS):
                    n = u.split('/')[-1]
                    if n == 'manifest.json': st['man'] += 1
                    else: st['parts'].append(n)
                    await r.fulfill(status=200, body=open('dl/' + n, 'rb').read(), headers={'access-control-allow-origin': '*', 'content-type': 'application/octet-stream'}); return
                if 'maps.mail.ru' in u:
                    st['over'] += 1
                    await r.fulfill(status=200, body=json.dumps({'elements': []}), headers={'content-type': 'application/json', 'access-control-allow-origin': '*'}); return
                if u.startswith('http://localhost') or 'cdnjs.cloudflare.com' in u: await r.continue_(); return
                await r.abort()
            await ctx.route('**/*', route)
            pg = await ctx.new_page(); errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            return ctx, pg, st, errs

        # ---------- Spotify: microfone do capacete ----------
        ctx, pg, st, errs = await ctx_for('')
        await pg.goto(URL); await pg.wait_for_timeout(1200)
        check('instalação nova: microfone do capacete desligado (a música não vai para o canal de ligação)', await pg.evaluate('TN.cfg.voiceBt') is False)
        await pg.evaluate("localStorage.setItem('tn_cfg',JSON.stringify({voiceBt:true,voice:true}));localStorage.removeItem('tn_mig278')")
        await pg.reload(); await pg.wait_for_timeout(1200)
        check('quem vinha da 2.7.7 com ele ligado: desliga uma vez (e guarda)', await pg.evaluate('TN.cfg.voiceBt') is False
              and json.loads(await pg.evaluate("localStorage.getItem('tn_cfg')"))['voiceBt'] is False)
        await pg.evaluate("localStorage.setItem('tn_cfg',JSON.stringify({...JSON.parse(localStorage.getItem('tn_cfg')),voiceBt:true}))")
        await pg.reload(); await pg.wait_for_timeout(1200)
        check('ligado de novo pelo dono: continua ligado (a migração é uma vez só)', await pg.evaluate('TN.cfg.voiceBt') is True)
        lab = await pg.evaluate("document.querySelector('#sVoiceBt').parentElement.textContent")
        check('Ajustes explicam que ligado a música abaixa', 'música não abaixar' in lab, lab)

        # ---------- no computador (sem tipo de conexão): nada baixa sozinho ----------
        await pg.wait_for_timeout(16500)
        check('sem tipo de conexão (computador/testes): não baixa mapa nem radares sozinho', st['man'] == 0 and not st['parts'] and st['over'] == 0, str(st))
        check('sem erros de página (1)', not errs, str(errs[:3]))
        await ctx.close()

        # ---------- Wi-Fi: o mapa e os radares baixam sozinhos ----------
        ctx, pg, st, errs = await ctx_for(conn('wifi'))
        await pg.goto(URL)
        await pg.evaluate('dlRetryMs=100')
        for _ in range(40):
            if await pg.evaluate('!!TN.offPM'): break
            await pg.wait_for_timeout(500)
        oi = await pg.text_content('#offInfo')
        check('Wi-Fi e nenhum mapa: baixa o mapa sozinho e abre', oi.startswith('Instalado') and len(st['parts']) == 3, oi + ' partes=%s' % st['parts'])
        check('… e guarda a cópia do índice', await pg.evaluate("JSON.parse(localStorage.getItem('tn_mapMan')).id") == 'teste-1')
        for _ in range(20):
            if st['over']: break
            await pg.wait_for_timeout(500)
        check('radares e lombadas de MG começam a baixar sozinhos', st['over'] > 0 and 'Baixando radares' in (await pg.text_content('#radInfo')), str(st['over']) + ' ' + await pg.text_content('#radInfo'))
        n0 = len(st['parts'])
        await pg.reload(); await pg.wait_for_timeout(10000)
        check('abrir de novo com o mapa completo: não baixa nada', len(st['parts']) == n0 and await pg.evaluate('!!TN.offPM'), str(st['parts']))

        # ---------- manifest.json vazio no aparelho (o que travava a 2.7.7) + uma parte estragada ----------
        await pg.evaluate('''(async()=>{const d=await (await navigator.storage.getDirectory()).getDirectoryHandle('mapa-dl');
          let w=await (await d.getFileHandle('manifest.json')).createWritable();await w.write('');await w.close();
          const h=await d.getFileHandle('small.pmtiles.part2');const f=await h.getFile();const b=new Uint8Array(await f.arrayBuffer());b[100]^=255;
          w=await h.createWritable();await w.write(b);await w.close();localStorage.removeItem('tn_mapMan')})()''')
        await pg.evaluate("Object.defineProperty(navigator,'connection',{configurable:true,get:()=>({type:'cellular',addEventListener(){}})})")
        await pg.add_init_script(conn('cellular'))
        await pg.reload(); await pg.wait_for_timeout(1800)
        oi = await pg.text_content('#offInfo')
        check('manifest vazio e sem cópia: não abre e explica (como na 2.7.7)', 'estão no aparelho' in oi and not await pg.evaluate('!!TN.offPM'), oi)
        p0 = list(st['parts'])
        await pg.wait_for_timeout(9000)   # automático nos dados móveis: confere o que tem e espera o Wi-Fi para a parte estragada
        oi = await pg.text_content('#offInfo')
        check('dados móveis: confere as partes, não baixa nada e diz que o resto vem no Wi-Fi', st['parts'] == p0 and 'baixa sozinho quando o celular estiver no Wi-Fi' in oi, oi)
        await pg.evaluate('downloadMap()')
        for _ in range(30):
            if await pg.evaluate('!!TN.offPM'): break
            await pg.wait_for_timeout(300)
        oi = await pg.text_content('#offInfo')
        check('"Baixar" à mão: baixa só a parte estragada (antes: "não consegui ler o mapa" para sempre) e o mapa abre',
              oi.startswith('Instalado') and st['parts'][len(p0):] == ['small.pmtiles.part2'], oi + ' novas=%s' % st['parts'][len(p0):])
        man = await pg.evaluate('''(async()=>JSON.parse(await (await (await (await (await navigator.storage.getDirectory()).getDirectoryHandle('mapa-dl')).getFileHandle('manifest.json')).getFile()).text()).id)()''')
        check('… e o manifest.json do aparelho volta a valer', man == 'teste-1', str(man))
        check('sem erros de página (2)', not errs, str(errs[:3]))
        await ctx.close()

        # ---------- dados móveis sem nada no aparelho: não baixa 1,4 GB sozinho ----------
        ctx, pg, st, errs = await ctx_for(conn('cellular'))
        await pg.goto(URL); await pg.wait_for_timeout(10000)
        oi = await pg.text_content('#offInfo')
        check('dados móveis e nenhum mapa: não baixa as partes e avisa que baixa no Wi-Fi', not st['parts'] and 'Wi-Fi' in oi, oi)

        # ---------- GPX que não abre: aviso (antes: nada acontecia) ----------
        await pg.evaluate("const _t=File.prototype.text;File.prototype.text=function(){return this.name==='ruim.gpx'?Promise.reject(new DOMException('o arquivo mudou','NotReadableError')):_t.call(this)};0")
        d = tempfile.mkdtemp(); f = os.path.join(d, 'ruim.gpx'); open(f, 'w').write(open('t.gpx').read())
        await pg.set_input_files('#fileIn', f); await pg.wait_for_timeout(600)
        t = await pg.text_content('#toast')
        check('abrir GPX que o celular não deixa ler: aviso com o motivo', 'Não consegui abrir ruim.gpx' in t and 'NotReadableError' in t, t)
        await pg.set_input_files('#fileIn', 't.gpx'); await pg.wait_for_timeout(800)
        check('… e um GPX bom continua abrindo', await pg.evaluate('!!TN.trackLine') if await pg.evaluate("'trackLine' in TN") else 'ruim' not in await pg.text_content('#toast'))
        check('sem erros de página (3)', not errs, str(errs[:3]))
        await ctx.close()
        await b.close()
    print('\nRESULTADO:', 'tudo certo' if not FAILS else 'FALHOU ' + str(FAILS))
    sys.exit(1 if FAILS else 0)

asyncio.run(main())
