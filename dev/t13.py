"""Pacote web do APK (android-app/www): precisa abrir sem CDN, com bibliotecas e fontes locais.
Antes: bash android-app/build-apk.sh --www-only ; servir android-app/www na porta 8766 (python3 -m http.server 8766)."""
import asyncio, sys
from playwright.async_api import async_playwright

FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        ctx = await b.new_context(viewport={'width': 1600, 'height': 720})
        pg = await ctx.new_page()
        errs, reqs, bad = [], [], []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: m.type == 'error' and 'net::ERR_FAILED' not in m.text and errs.append(m.text))   # ERR_FAILED = tile externo que o teste aborta de propósito
        pg.on('request', lambda r: reqs.append(r.url))
        pg.on('response', lambda r: r.status >= 400 and r.url.startswith('http://localhost:8766') and bad.append((r.status, r.url)))
        # sem internet: o que não for do próprio pacote falha (tiles externos são esperados)
        await pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith('http://localhost') else r.abort())
        await pg.goto('http://localhost:8766/index.html?trilha=1'); await pg.wait_for_timeout(2500)
        ext = sorted({u.split('/')[2] for u in reqs if not u.startswith('http://localhost')})
        check('nenhum pedido a CDN ou a Google Fonts (cdnjs, fonts.googleapis, fonts.gstatic)', not any(h in ('cdnjs.cloudflare.com', 'fonts.googleapis.com', 'fonts.gstatic.com') for h in ext), str(ext))
        check('nenhum arquivo do pacote devolveu erro 4xx/5xx', not bad, str(bad))
        r = await pg.evaluate("({L:typeof L,rot:typeof L.Map.prototype.setBearing,pdf:typeof pdfjsLib,cap:typeof Capacitor,native:Capacitor.isNativePlatform(),elev:typeof L.control.elevation,pm:typeof pmtiles,orb:document.fonts.check('900 20px Orbitron'),inter:document.fonts.check('400 14px Inter')})")
        check('Leaflet, leaflet-rotate, leaflet-elevation, pdf.js, PMTiles e Capacitor carregaram do pacote', r['L'] == 'object' and r['rot'] == 'function' and r['pdf'] == 'object' and r['cap'] == 'object' and r['elev'] == 'function' and r['pm'] == 'object', str(r))
        check('Capacitor no navegador comum não se diz nativo (o app segue o caminho web)', r['native'] is False)
        check('fontes Orbitron e Inter locais disponíveis', r['orb'] and r['inter'], str((r['orb'], r['inter'])))
        # GPX + PDF funcionam com o worker local do pdf.js
        await pg.set_input_files('#fileIn', 't.gpx'); await pg.wait_for_timeout(600)
        await pg.set_input_files('#fileIn', 'rb.pdf'); await pg.wait_for_timeout(2500)
        r = await pg.evaluate("({wps:TN.wps.length,canv:document.querySelectorAll('#rb canvas').length})")
        check('abre GPX e PDF (worker do pdf.js local)', r['wps'] == 3 and r['canv'] == 3, str(r))
        check('cdnjs não foi tocado nem para o worker', not any('cdnjs' in u for u in reqs))
        check('sem erros de console', not errs, str(errs))
        await b.close()
    print('\nRESULTADO:', 'FALHOU ' + str(FAILS) if FAILS else 'tudo certo')
    sys.exit(1 if FAILS else 0)
asyncio.run(main())
