"""Correções da revisão de segurança: backup de ajustes, rótulo do mapa, tile MVT malformado, pdf.js sem eval."""
import asyncio, sys, json, os, tempfile
from playwright.async_api import async_playwright

FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

TMP = tempfile.mkdtemp(prefix='tn12_')

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        pg = await (await b.new_context(viewport={'width': 1600, 'height': 720})).new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
        await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(1300)

        # ---- backup de ajustes malicioso ----
        evil = {'cfg': {'mult': 'x', 'wpR': 'abc', 'step': 0.05, 'dayMode': 'night', 'naoExiste': 'lixo', 'voice': 1, 'compSpd': 12},
                'keys': {'chrono': '<img src=x onerror=window.__pwn=1>', 'lock': 'KeyZ', 'fantasma': 'KeyQ', 'zoomIn': 'a' * 500}}
        path = os.path.join(TMP, 'ajustes.json'); open(path, 'w').write(json.dumps(evil))
        await pg.evaluate("document.querySelector('#bSet').click()"); await pg.set_input_files('#restoreIn', path); await pg.wait_for_timeout(500)
        r = await pg.evaluate('''()=>({mult:TN.cfg.mult,wpR:TN.cfg.wpR,step:TN.cfg.step,dayMode:TN.cfg.dayMode,x:TN.cfg.naoExiste,voice:TN.cfg.voice,compSpd:TN.cfg.compSpd,
          chrono:[...document.querySelectorAll('#keyList [data-a=chrono]')].map(b=>b.textContent)[0],lock:[...document.querySelectorAll('#keyList [data-a=lock]')].map(b=>b.textContent)[0],zoomIn:[...document.querySelectorAll('#keyList [data-a=zoomIn]')].map(b=>b.textContent)[0],pwn:window.__pwn})''')
        check('valores de tipo errado são ignorados (mult/wpR/voice)', r['mult'] == 1 and r['wpR'] == 90 and r['voice'] is True, str(r))
        check('valores válidos são aplicados (step, dayMode, compSpd, tecla lock)', r['step'] == 0.05 and r['dayMode'] == 'night' and r['compSpd'] == 12 and r['lock'] == 'KeyZ', str(r))
        check('chave desconhecida não entra', r['x'] is None)
        check('tecla com HTML e tecla gigante são recusadas (voltam ao padrão)', r['chrono'] == 'KeyC' and r['zoomIn'] == 'Equal', str((r['chrono'], r['zoomIn'])))
        check('nada executou', r['pwn'] is None)
        # mesmo que um valor estranho já esteja no localStorage, as teclas aparecem escapadas
        await pg.evaluate('''()=>{localStorage.setItem('tn_keys',JSON.stringify({chrono:'<img src=x onerror=window.__pwn=2>'}))}''')
        await pg.reload(); await pg.wait_for_timeout(1200); await pg.evaluate("document.querySelector('#bSet').click()"); await pg.wait_for_timeout(300)
        check('tecla já gravada com HTML aparece como texto', await pg.evaluate("window.__pwn===undefined&&document.querySelector('#keyList [data-a=chrono]').textContent.startsWith('<img')"))
        await pg.evaluate("document.querySelector('#dlgSet').close()")

        # ---- tile MVT malformado ----
        r = await pg.evaluate('''()=>{const out={};
          const t0=performance.now();
          try{TN.mvtRoads(new Uint8Array([0x1a,0xff,0xff,0xff,0xff,0x0f]).buffer);out.a='sem erro'}catch(e){out.a=String(e.message)}
          try{TN.mvtRoads(new Uint8Array([0x1a,0x05,0x0a]).buffer);out.b='sem erro'}catch(e){out.b=String(e.message)}
          // camada "roads" com uma feição cuja geometria diz ter 2^29 pontos mas traz poucos bytes
          const enc=s=>[...new TextEncoder().encode(s)];const feat=[0x18,0x02,0x22,0x05,0x09,0xff,0xff,0xff,0x3f];   // tipo=2, geometria: comando MoveTo com contagem gigante
          const lay=[0x0a,0x05,...enc('roads'),0x12,feat.length,...feat];const tile=[0x1a,lay.length,...lay];
          try{const f=TN.mvtRoads(new Uint8Array(tile).buffer);out.c=f.length}catch(e){out.c=String(e.message)}
          out.ms=performance.now()-t0;return out}''')
        check('tile truncado ou com tamanho absurdo dá erro rápido, sem travar', r['ms'] < 500 and 'sem erro' not in (r['a'], ), str(r))
        check('geometria com contagem gigante não gira em laço', r['ms'] < 500, str(r['c']))

        # ---- PDF abre sem eval ----
        src = open('../index.html', encoding='utf-8').read()
        check('getDocument é chamado com isEvalSupported:false (CVE-2024-4367)', 'getDocument({data:buf,isEvalSupported:false})' in src)
        await pg.set_input_files('#fileIn', 'rb.pdf'); await pg.wait_for_timeout(2000)
        check('o PDF continua abrindo', await pg.evaluate("document.querySelectorAll('#rb canvas').length") == 3)


        # ---- digitar nota não dispara as teclas do controle ----
        await pg.evaluate('()=>{TN.st.partial=3.21;TN.st.total=10;TN.onPos({timestamp:Date.now(),coords:{latitude:-20,longitude:-44,altitude:0,accuracy:5,speed:0,heading:null}})}')
        await pg.evaluate("document.querySelector('#bNote').click()"); await pg.click('#noteTx')
        await pg.keyboard.type('cl=- ponte'); await pg.keyboard.press('Enter'); await pg.keyboard.press('ArrowLeft'); await pg.keyboard.press('ArrowRight'); await pg.keyboard.press('Backspace')
        r = await pg.evaluate("({p:TN.st.partial,t:TN.st.total,v:document.querySelector('#noteTx').value,lock:document.querySelector('#lockIco').textContent})")
        check('digitando na nota: PARCIAL, TOTAL e trava de toque não mudam, e o texto é digitado', abs(r['p'] - 3.21) < 1e-9 and r['t'] == 10 and r['v'] == 'cl=- ponte' and r['lock'] == '🔓', str(r))
        await pg.evaluate("()=>{document.querySelector('#toast').textContent='';document.dispatchEvent(new KeyboardEvent('keydown',{key:'a',code:'',bubbles:true}))}")
        check('tecla com code vazio (teclado virtual) não aciona ação nenhuma', 'música' not in await pg.text_content('#toast'))
        # toque duplo em "Salvar nota"
        await pg.fill('#noteTx', 'uma só'); await pg.evaluate("()=>{const b=document.querySelector('#noteSave');b.click();b.click()}"); await pg.wait_for_timeout(700)
        check('toque duplo em Salvar cria uma nota só', await pg.evaluate('TN.rnotes.length') == 1, str(await pg.evaluate('TN.rnotes.length')))
        await pg.evaluate("document.querySelector('#dlgNote').close()")

        # ---- tile MVT com camadas fora de ordem e campo desconhecido ----
        r = await pg.evaluate("""()=>{const vi=n=>{const o=[];while(n>127){o.push((n&127)|128);n=Math.floor(n/128)}o.push(n);return o};
          const enc=s=>[...new TextEncoder().encode(s)],str=(f,s)=>{const b=enc(s);return [(f<<3)|2,...vi(b.length),...b]},msg=(f,b)=>[(f<<3)|2,...vi(b.length),...b];
          const feat=[0x7a,0x03,1,2,3, 0x12,0x02,0,0, 0x18,0x02, 0x22,0x06,9,0,0,10,10,10];     // campo 15 desconhecido (len 3), tags, tipo=2, MoveTo + LineTo
          const roads=[...str(1,'roads'),...msg(2,feat),...str(3,'kind'),...msg(4,str(1,'minor_road')),0x28,0x80,0x20];
          const earth=[...str(1,'earth'),...str(3,'k'),...msg(4,str(1,'v')),0x28,0x80,0x20];
          const tile=[...msg(3,earth),...msg(3,roads),...msg(3,earth)];
          const f=TN.mvtRoads(new Uint8Array(tile).buffer);return {n:f.length,kind:f[0]&&f[0].props.kind,lines:f[0]&&JSON.stringify(f[0].lines),ext:f[0]&&f[0].ext}}""")
        check('decodifica a camada roads no meio de outras, com chaves/valores depois das feições e campo desconhecido', r == {'n': 1, 'kind': 'minor_road', 'lines': '[[[0,0],[5,5]]]', 'ext': 4096}, str(r))

        # ---- GPX: identidade por pasta, zonas fora de ordem, ponto inválido ----
        K = 0.0095699
        gp = lambda order, extra='': '<?xml version="1.0"?><gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">' + ''.join(f'<wpt lat="-20" lon="{-44 + km * K:.6f}"><name>{n}</name></wpt>' for km, n in order) + '<trk><trkseg>' + ''.join(f'<trkpt lat="-20" lon="{-44 + i * 0.1 * K:.6f}"/>' for i in range(61)) + extra + '</trkseg></trk></gpx>'
        base = gp([(1, 'WP1'), (2, 'VEL 40'), (3, 'FIM')])
        await pg.evaluate('(x)=>TN.loadGPX(x,"t.gpx",{parts:["gpx","Dia1"],name:"t.gpx"})', base)
        await pg.evaluate("()=>{TN.wpState[0]='ok'}")
        await pg.evaluate('(x)=>TN.loadGPX(x,"t.gpx",{parts:["gpx","Dia1"],name:"t.gpx"})', base)
        same = await pg.evaluate('TN.wpState[0]')
        await pg.evaluate('(x)=>TN.loadGPX(x,"t.gpx",{parts:["gpx","Dia2"],name:"t.gpx"})', base)
        diff = await pg.evaluate('TN.wpState[0]')
        check('mesmo arquivo reaberto mantém o progresso; mesmo nome em outra pasta começa do zero', same == 'ok' and diff is None, str((same, diff)))
        await pg.evaluate("()=>{localStorage.setItem('tn_zones_gpx/Dia1/t.gpx#'+0,'x')}")
        await pg.evaluate('(x)=>TN.loadGPX(x,"fora.gpx")', gp([(3, 'FIM'), (2, 'VEL 40'), (1, 'WP1')]))
        z = await pg.evaluate('TN.zones.map(z=>[z.limit,+z.from.toFixed(2),+z.to.toFixed(2)])')
        check('waypoints fora de ordem (FIM antes de VEL 40) ainda formam a zona certa', z == [[40, 2.0, 3.0]], str(z))
        await pg.evaluate('(x)=>TN.loadGPX(x,"virgula.gpx")', gp([(1, 'WP1')], '<trkpt lat="45,5" lon="-44"/><trkpt lat="abc" lon="x"/>'))
        r = await pg.evaluate('({km:TN.rbNotes.map(n=>n.km),w:TN.wps.map(w=>w.km)})')
        check('ponto com lat "45,5" ou texto é descartado: nenhum km vira NaN', all(isinstance(v, (int, float)) for v in r['km'] + r['w']) and len(r['km']) >= 2, str(r))

        # ---- rótulo do mapa offline escapado ----
        await pg.set_input_files('#offIn', 'small.pmtiles'); await pg.wait_for_timeout(3000)
        check('sem erros', not errs, str(errs))
        await b.close()
    print('\nRESULTADO:', 'FALHOU ' + str(FAILS) if FAILS else 'tudo certo')
    sys.exit(1 if FAILS else 0)
asyncio.run(main())
