"""Fumaça do app (v2.7, sem as funções de rali): abre, GPS anda, telas, GPX só para ver no mapa, sem restos de rali."""
import asyncio, sys
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html'
FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        pg = await b.new_page(viewport={'width': 1280, 'height': 720})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
        await pg.goto(URL); await pg.wait_for_timeout(2000)
        check('abre no Mapa', await pg.evaluate("document.querySelector('#paneMap').classList.contains('on')"))
        ids = await pg.evaluate("[...document.querySelectorAll('[id]')].map(e=>e.id)")
        gone = [i for i in ['paneRb', 'total', 'partial', 'bSplit', 'bElev', 'bWp', 'bChrono', 'bBack', 'bResetP', 'dlgWp', 'dlgZones', 'sSim', 'sMult', 'sTrail', 'mOpen'] if i in ids]
        check('sem restos de rali na página', not gone, str(gone))
        check('sem pdf.js nem altimetria carregados', await pg.evaluate("typeof pdfjsLib==='undefined'&&typeof L.control.elevation==='undefined'"))
        # GPS anda 100 pontos para o nordeste
        r = await pg.evaluate('''()=>{const t=Date.now();for(let i=0;i<=100;i++){TN.onPos({timestamp:t+i*2000,coords:{latitude:-23.55+i*0.0003,longitude:-46.63+i*0.0002,altitude:800,accuracy:5,speed:null,heading:null}})}
          return {mov:TN.st.movKm,spd:+document.querySelector('#speed').textContent,cap:document.querySelector('#cap').textContent,lab:document.querySelector('#wpLabel').textContent}}''')
        check('GPS: velocidade e km em movimento contam', r['spd'] > 30 and 3.5 < r['mov'] < 4.5, str(r))
        check('CAP sem rota mostra "sem rota"', r['cap'] == '---' and r['lab'] == 'sem rota', str(r))
        # GPX só para ver
        await pg.set_input_files('#fileIn', 't.gpx'); await pg.wait_for_timeout(600)
        st = await pg.evaluate("({n:TN.track.length,name:document.querySelector('#fileName').textContent,map:document.querySelector('#paneMap').classList.contains('on')})")
        check('GPX aberto aparece no mapa (só para ver)', st['n'] > 1 and st['name'] == 't.gpx' and st['map'], str(st))
        await pg.click('#fileName'); await pg.wait_for_timeout(200)
        check('tocar no nome tira o trajeto do mapa', await pg.evaluate('TN.track.length') == 0 and await pg.text_content('#fileName') == '')
        # telas e janelas principais abrem
        for sel in ['[data-pane=paneDash]', '#bMore', '#bSet', '#bGpx', '#bNav', '#bNote', '#bSpot']:
            await pg.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close());document.querySelector(%r).click()" % sel); await pg.wait_for_timeout(250)
        await pg.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
        dk = await pg.evaluate("[...document.querySelectorAll('#dash [data-k]')].map(e=>e.dataset.k)")
        check('Painel sem mostradores de rali', dk and not ({'chrono', 'wps', 'rest', 'corr'} & set(dk)), str(dk))
        check('ajustes sem as opções do rali', await pg.evaluate("Object.keys(TN.cfg).every(k=>!['mult','wpR','zoneOn','sim','rbReset'].includes(k))"))
        # v2.7.2: saiu o controle de guidão (teclas configuráveis); as teclas antigas não fazem mais nada
        z0 = await pg.evaluate('TN.map.getZoom()')
        for k in ('Equal', 'Minus', 'KeyL', 'Tab'): await pg.keyboard.press(k)
        await pg.wait_for_timeout(200)
        r = await pg.evaluate("({z:TN.map.getZoom(),lock:document.querySelector('#lockIco').textContent,lista:!!document.querySelector('#keyList,#bKeyDef'),h:[...document.querySelectorAll('#dlgSet h3')].map(h=>h.textContent).filter(t=>/guid|teclad/i.test(t))})")
        check('sem controle de guidão: Ajustes sem teclas e =, -, L, Tab não mudam nada', r['z'] == z0 and r['lock'] == '🔓' and not r['lista'] and not r['h'], str(r))
        await pg.set_viewport_size({'width': 420, 'height': 860}); await pg.wait_for_timeout(300)
        check('sem erros de console', not errs, str(errs))
        await b.close()
    print('\nRESULTADO:', 'tudo certo' if not FAILS else 'FALHOU ' + str(FAILS))
    sys.exit(1 if FAILS else 0)

asyncio.run(main())
