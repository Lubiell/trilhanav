"""Caça a erros (v2.0.1): cada bloco reproduz um erro confirmado e confere a correção.
Precisa de rb.pdf e t.gpx em dev/ e do app em http://localhost:8765."""
import asyncio, sys, math, base64
from playwright.async_api import async_playwright

FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

URL = 'http://localhost:8765/index.html?trilha=1'
K = 0.0095699
M_LAT = 111194.9; M_LON = M_LAT * math.cos(math.radians(20))
T0 = 1_000_000_000_000

def gpx(wps, n=61):
    return ('<?xml version="1.0"?><gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">'
            + ''.join(f'<wpt lat="-20" lon="{-44 + km * K:.6f}"><name>{nm}</name></wpt>' for km, nm in wps)
            + '<trk><trkseg>' + ''.join(f'<trkpt lat="-20" lon="{-44 + i * 0.1 * K:.6f}"/>' for i in range(n)) + '</trkseg></trk></gpx>')
A = gpx([(1, 'A1'), (2, 'A2'), (3, 'A3'), (4, 'A4')]); B = gpx([(1, 'B1'), (2, 'B2'), (3, 'B3'), (4, 'B4'), (5, 'B5')])

class Rnd:
    def __init__(self, seed): self.s = seed
    def __call__(self):
        self.s = (self.s * 1103515245 + 12345) & 0x7fffffff; return (self.s % 2001) / 1000 - 1

def recorded(noise, stop_s, with_time=True, seed=7):
    """trilha gravada a 1 Hz: 1,5 km reto a 36 km/h, parada de stop_s segundos (GPS passeando ±noise m), mais 1,5 km reto."""
    r = Rnd(seed); pts = []
    for i in range(150): pts.append((i * 10.0 + r() * 2, r() * 2))
    for i in range(stop_s): pts.append((1500 + r() * noise, r() * noise))
    for i in range(1, 150): pts.append((1500 + i * 10.0 + r() * 2, r() * 2))
    tm = lambda i: '<time>2026-11-15T12:%02d:%02dZ</time>' % (i // 60, i % 60) if with_time else ''
    return ('<?xml version="1.0"?><gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1"><wpt lat="-20" lon="%.7f"><name>Fim</name></wpt><trk><trkseg>' % (-44 + 2990 / M_LON)
            + ''.join(f'<trkpt lat="{-20 + py / M_LAT:.7f}" lon="{-44 + px / M_LON:.7f}">{tm(i)}</trkpt>' for i, (px, py) in enumerate(pts)) + '</trkseg></trk></gpx>')

def hairpin():
    """ida de 300 m, retorno fechado (pernas a 8 m uma da outra) e volta de 300 m, a 18 km/h com hora: não pode ser confundido com parada."""
    pts = [(i * 5.0, 0.0) for i in range(61)]
    for k in range(1, 6): a = math.pi * k / 6; pts.append((300 + 4 * math.sin(a), 4 - 4 * math.cos(a)))
    pts += [(300 - i * 5.0, 8.0) for i in range(61)]
    return ('<?xml version="1.0"?><gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>'
            + ''.join(f'<trkpt lat="{-20 + py / M_LAT:.7f}" lon="{-44 + px / M_LON:.7f}"><time>2026-11-15T12:%02d:%02dZ</time></trkpt>' % (i // 60, i % 60) for i, (px, py) in enumerate(pts)) + '</trkseg></trk></gpx>')

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

        # 1) trocar de GPX e reabrir o app: o novo não herda os waypoints validados do anterior
        pg, errs = await page(b)
        await pg.evaluate('(x)=>TN.loadGPX(x,"a.gpx")', A); await pg.evaluate(RIDE, [T0, K, 120])
        check('preparo: 3 waypoints validados no GPX A', await pg.evaluate('TN.wpState') == ['ok', 'ok', 'ok', None])
        await pg.evaluate('(x)=>TN.loadGPX(x,"b.gpx")', B); await pg.reload(); await pg.wait_for_timeout(1300)
        r = await pg.evaluate('({st:TN.wpState,idx:TN.st.wpIdx,wp:document.querySelector("#wpLabel").textContent})')
        check('GPX B reaberto começa do zero (antes: mostrava "B4 (4/5)" com 3 validados)', r['st'] == [None] * 5 and r['idx'] == 0 and r['wp'].startswith('B1'), str(r))
        await pg.context.close()

        # 2) "Marcar aqui" e reabrir: a marca continua na lista e os estados não desalinham
        pg, errs = await page(b)
        await pg.evaluate('(x)=>TN.loadGPX(x,"a.gpx")', A); await pg.evaluate(RIDE, [T0, K, 50])
        await pg.evaluate("document.querySelector('#bWp').click()"); await pg.click('#bMarkWp'); await pg.wait_for_timeout(200)
        antes = await pg.evaluate('({n:TN.wps.map(w=>w.name),st:TN.wpState,idx:TN.st.wpIdx,rb:TN.rbNotes.map(n=>n.name)})')
        await pg.reload(); await pg.wait_for_timeout(1300)
        dep = await pg.evaluate('({n:TN.wps.map(w=>w.name),st:TN.wpState,idx:TN.st.wpIdx,rb:TN.rbNotes.map(n=>n.name)})')
        check('a marca volta no mesmo lugar e os estados continuam alinhados', dep['n'] == antes['n'] and dep['st'] == antes['st'] == ['ok', 'ok', None, None, None] and dep['idx'] == antes['idx'] == 2 and dep['n'][1].startswith('Marcado'), str(dep))
        check('a marca aparece no roadbook, antes e depois de reabrir', any(x.startswith('Marcado') for x in antes['rb']) and antes['rb'] == dep['rb'], str(dep['rb']))
        await pg.evaluate('(x)=>TN.loadGPX(x,"b.gpx")', B)
        check('outro GPX não herda a marca', not any(n.startswith('Marcado') for n in await pg.evaluate('TN.wps.map(w=>w.name)')))
        await pg.context.close()

        # 3) GPX grande demais para o localStorage: o progresso sobrevive a reabrir
        pg, errs = await page(b, "const __si=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k==='tn_gpx')throw new DOMException('QuotaExceededError');return __si.call(this,k,v)};")
        await pg.evaluate('(x)=>TN.loadGPX(x,"grande.gpx")', A); await pg.wait_for_timeout(600); await pg.evaluate(RIDE, [T0, K, 80])
        await pg.reload(); await pg.wait_for_timeout(1500)
        r = await pg.evaluate('({st:TN.wpState,idx:TN.st.wpIdx,wps:TN.wps.length})')
        check('GPX grande reaberto do armazenamento mantém o progresso', r == {'st': ['ok', 'ok', None, None], 'idx': 2, 'wps': 4}, str(r))
        await pg.context.close()

        # 4) primeira posição imprecisa não soma distância
        pg, errs = await page(b)
        await pg.evaluate(POS, [-20.0, -44.0, T0, 800, None])
        await pg.evaluate(POS, [-20.0, -44.0 + 0.6 * K, T0 + 12000, 6, 0]); await pg.evaluate(POS, [-20.0, -44.0 + 0.6 * K, T0 + 13000, 6, 0])
        check('posição de rede (±800 m) seguida de GPS bom a 600 m: TOTAL continua 0 (antes: 0,60 km)', await pg.evaluate('TN.st.total') == 0, str(await pg.evaluate('TN.st.total')))
        await pg.evaluate(POS, [-20.0, -44.0 + 0.7 * K, T0 + 23000, 6, 10])
        check('depois disso o odômetro conta normalmente (100 m)', abs(await pg.evaluate('TN.st.total') - 0.1) < 0.005, str(await pg.evaluate('TN.st.total')))
        await pg.context.close()

        # 5) trilha gravada com parada: sem curvas falsas e sem km inflado
        pg, errs = await page(b)
        for nome, g, tol_km, max_falsas in (('parada de 2 min, ruído ±4 m, com hora', recorded(4, 120), 0.02, 0),
                                              ('parada de 5 min, ruído ±8 m, com hora', recorded(8, 300), 0.03, 0),
                                              ('parada de 2 min, ruído ±4 m, SEM hora', recorded(4, 120, with_time=False), 0.06, 2)):
            await pg.evaluate('([x,n])=>TN.loadGPX(x,n)', [g, nome + '.gpx']); await pg.wait_for_timeout(200)
            r = await pg.evaluate('({notas:TN.rbNotes.map(n=>n.name),km:TN.wps[0].km,pts:TN.track.length})')
            falsas = [n for n in r['notas'] if n not in ('Largada', 'Chegada', 'Fim')]
            check(f'{nome}: reta de 2,99 km fica com {len(falsas)} curva(s) falsa(s) (máx. {max_falsas}) e km {r["km"]:.2f}', len(falsas) <= max_falsas and abs(r['km'] - 2.99) <= tol_km, f'{r["pts"]} pontos; {falsas}')
        await pg.evaluate('(x)=>TN.loadGPX(x,"retorno.gpx")', hairpin()); await pg.wait_for_timeout(200)
        r = await pg.evaluate('({notas:TN.rbNotes.map(n=>[n.name,Math.round(n.A||0)]),km:TN.rbNotes[TN.rbNotes.length-1].km})')
        check('retorno fechado de verdade (pernas a 8 m) não é confundido com parada', any(n[0].startswith('Retorno') for n in r['notas']) and abs(r['km'] - 0.6126) < 0.02, str(r))
        check('sem erros (trilho)', not errs, str(errs))
        await pg.context.close()

        # 6) retorno em linha reta: acompanha a posição sem repetir "Rota recalculada"
        pg, errs = await page(b, SPEECH)
        await pg.evaluate('(x)=>TN.loadGPX(x,"a.gpx")', A)
        await pg.evaluate(POS, [-20.02, -44.0 + 2 * K, T0, 5, 0]); await pg.evaluate(POS, [-20.02, -44.0 + 2 * K, T0 + 1000, 5, 0])
        await pg.evaluate("document.querySelector('#bBack').click()"); await pg.wait_for_timeout(500)
        for i in range(1, 121):
            await pg.evaluate(POS, [-20.02, -44.0 + 2 * K + i * 0.01 * K, T0 + 1000 + i * 1000, 5, 10])
        await pg.wait_for_timeout(300)
        spk = await pg.evaluate('TN.spoken')
        r = await pg.evaluate('({lon0:TN.rtBack.pts[0].lon,len:TN.rtBack.len,lbl:document.querySelector("#wpLabel").textContent,cap:document.querySelector("#cap").textContent,linha:TN.rtLayer.getLatLngs()[0].lng})')
        check('2 minutos fora da linha: só a fala inicial (antes: "Rota recalculada" 7 vezes)', len(spk) == 1 and spk[0].startswith('Caminho de volta'), str(spk))
        check('a linha reta acompanha a posição (começa em você, ~2,2 km até a trilha, CAP norte)', abs(r['lon0'] - (-44.0 + 3.2 * K)) < 1e-6 and abs(r['linha'] - r['lon0']) < 1e-9 and 2150 < r['len'] < 2300 and r['cap'] == '000°' and 'VOLTAR' in r['lbl'], str(r))
        for i in range(1, 60):
            await pg.evaluate(POS, [-20.02 + i * 0.0004, -44.0 + 3.2 * K, T0 + 200000 + i * 2000, 5, 10])
        check('chegando à trilha o retorno é encerrado', await pg.evaluate('TN.rtBack') is None and (await pg.evaluate('TN.spoken'))[-1] == 'De volta à trilha')
        check('sem erros (retorno)', not errs, str(errs))
        await pg.context.close()

        # 7) simulação + GPX do gerenciador: funciona depois de reabrir
        pg, errs = await page(b)
        await pg.evaluate("document.querySelector('#bGpx').click()"); await pg.set_input_files('#gImportIn', 't.gpx'); await pg.wait_for_timeout(500)
        await pg.click('[data-act=open]'); await pg.wait_for_timeout(400)
        await pg.evaluate("()=>{TN.cfg.sim=true;localStorage.setItem('tn_cfg',JSON.stringify(TN.cfg))}")
        await pg.reload(); await pg.wait_for_timeout(4000)
        r = await pg.evaluate('({total:TN.st.total,gps:document.querySelector("#gpsTxt").textContent})')
        check('a simulação começa sozinha ao reabrir (antes: ficava parada em "GPS ---")', r['total'] > 0.02 and r['gps'].startswith('GPS ±'), str(r))
        await pg.context.close()

        # 8) PDF aberto depois do GPX é desenhado na largura da tela
        pg, errs = await page(b)
        await pg.evaluate('(x)=>TN.loadGPX(x,"a.gpx")', A)
        await pg.set_input_files('#fileIn', 'rb.pdf'); await pg.wait_for_timeout(2500)
        r = await pg.evaluate("({canvasW:document.querySelector('#rb canvas').width,paneW:document.querySelector('#rb').clientWidth})")
        check('PDF na largura do painel (antes: 600 px esticados)', r['canvasW'] == r['paneW'] > 1000, str(r))
        await pg.context.close()

        # 9) zonas pelo nome do waypoint: só palavra inteira
        pg, errs = await page(b)
        casos = [(['Nivel 50', 'Mirante'], []), (['Nível 50', 'X'], []), (['Travel 40', 'Mirante'], []), (['Marvel 100', 'X'], []),
                 (['VEL 40', 'Enduro Park', 'FIM'], [[40, 1.0, 3.0]]), (['Vel. 40', 'Fim da zona'], [[40, 1.0, 2.0]]), (['VEL40', 'X', 'END'], [[40, 1.0, 3.0]]),
                 (['Limite 30', 'X'], [[30, 1.0, 6.0]]), (['ZV 50', 'Livre'], [[50, 1.0, 2.0]]), (['Zona de velocidade 60 km/h', 'FIM'], [[60, 1.0, 2.0]])]
        for i, (nomes, esperado) in enumerate(casos):
            await pg.evaluate('([x,n])=>TN.loadGPX(x,n)', [gpx([(k + 1, n) for k, n in enumerate(nomes)]), f'z{i}.gpx'])
            z = await pg.evaluate('TN.zones.map(z=>[z.limit,+z.from.toFixed(1),+z.to.toFixed(1)])')
            check(f'{nomes} -> {esperado}', z == esperado, str(z))
        await pg.context.close()

        # 10) no APK, exportar entrega o arquivo pela tela de compartilhar (o WebView não baixa)
        pg, errs = await page(b, FAKE_CAP)
        await pg.evaluate("()=>{window.__a=0;const o=HTMLAnchorElement.prototype.click;HTMLAnchorElement.prototype.click=function(){if(this.download)window.__a++;return o.call(this)}}")
        await pg.evaluate('(x)=>TN.loadGPX(x,"a.gpx")', A)
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

        # 12) celular deitado (guidão): os quatro mostradores cabem sem rolar
        for w, h in ((740, 360), (915, 412), (568, 320)):
            ctx = await b.new_context(viewport={'width': w, 'height': h}, has_touch=True, is_mobile=True); pg = await ctx.new_page()
            await pg.goto(URL); await pg.wait_for_timeout(1000)
            await pg.evaluate('(x)=>TN.loadGPX(x,"a.gpx")', A)
            await pg.evaluate("()=>{TN.st.total=1234.56;TN.st.partial=987.65;const t=Date.now();for(let i=0;i<2;i++)TN.onPos({timestamp:t+i*1000,coords:{latitude:-20,longitude:-44+i*0.0003,altitude:0,accuracy:5,speed:33,heading:271}})}")
            r = await pg.evaluate("""()=>{const s=document.querySelector('#side'),sb=s.getBoundingClientRect();return {rola:s.scrollHeight-s.clientHeight,
              fora:['#total','#partial','#cap','#speed'].filter(q=>{const r=document.querySelector(q).getBoundingClientRect();return r.bottom>sb.bottom+1||r.top<sb.top-1}),
              estouro:['#total','#partial','#cap','#speed'].filter(q=>{const e=document.querySelector(q);return e.scrollWidth>e.clientWidth})}}""")
            check(f'{w}x{h}: TOTAL, PARCIAL, CAP e VELOCIDADE visíveis sem rolar (antes: velocidade fora da tela)', r['rola'] <= 0 and not r['fora'] and not r['estouro'], str(r))
            await ctx.close()

        # 11) offline de verdade: sem rede e com o cache HTTP limpo, só resta o que o service worker guardou
        ctx = await b.new_context(viewport={'width': 1600, 'height': 720}); pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(URL); await pg.wait_for_timeout(800)
        await pg.evaluate("(async()=>{await navigator.serviceWorker.register('sw.js');await navigator.serviceWorker.ready})()")
        await pg.wait_for_timeout(5000); await pg.reload(); await pg.wait_for_timeout(3000)
        await pg.evaluate('(x)=>TN.loadGPX(x,"a.gpx")', A)
        await pg.evaluate("fetch('NOTICE.md').then(r=>r.text())"); await pg.wait_for_timeout(1500)
        c = await pg.evaluate('''(async()=>{const v=(await caches.keys()).find(k=>/^trilhanav-v/.test(k));const us=(await (await caches.open(v)).keys()).map(r=>r.url);return {v,notice:us.some(u=>/NOTICE/.test(u)),css:us.filter(u=>/fonts\\.googleapis/.test(u)).length,woff:us.filter(u=>/fonts\\.gstatic/.test(u)).length}})()''')
        check('o service worker guarda em tempo de uso (arquivo fora da lista fixa e as fontes)', c['notice'] and c['css'] >= 1 and c['woff'] >= 2, str(c))
        await ctx.set_offline(True)
        cdp = await ctx.new_cdp_session(pg); await cdp.send('Network.clearBrowserCache')
        await pg.reload(); await pg.wait_for_timeout(3500)
        r = await pg.evaluate('''()=>{const w=f=>{const s=document.createElement('span');s.style.cssText='font:900 40px '+f+';position:absolute;visibility:hidden';s.textContent='0123456789';document.body.appendChild(s);const x=s.offsetWidth;s.remove();return x};
          return {L:typeof L,pdf:typeof pdfjsLib,tn:typeof TN,gpx:window.TN?TN.wps.length:null,orb:[...document.fonts].some(f=>/Orbitron/.test(f.family)&&f.status==='loaded'),wOrb:w('Orbitron,monospace'),wMono:w('monospace')}}''')
        check('sem internet o app abre com o GPX', r['L'] == 'object' and r['pdf'] == 'object' and r['tn'] == 'object' and r['gpx'] == 4, str(r))
        check('sem internet as fontes continuam (antes: os números caíam para a fonte padrão)', r['orb'] and r['wOrb'] != r['wMono'], str(r))
        miss = await pg.evaluate("fetch('nao-existe.js').then(r=>r.status+' '+(r.headers.get('content-type')||'')).catch(e=>'falhou')")
        check('arquivo que não está no cache falha de verdade, em vez de vir o index.html no lugar', miss == 'falhou', miss)
        check('sem erros (offline)', not errs, str(errs))
        await b.close()
    print('\nRESULTADO:', 'FALHOU ' + str(FAILS) if FAILS else 'tudo certo')
    sys.exit(1 if FAILS else 0)
asyncio.run(main())
