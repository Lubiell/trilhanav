"""Etapa 3: rotação do mapa (leaflet-rotate) e perfil de altimetria (leaflet-elevation)."""
import asyncio, sys, math
from playwright.async_api import async_playwright

FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

K = 0.0095699
def gpx(ele=True):
    # 10 km para leste com uma subida de 300 m e descida
    pts = ''.join(f'<trkpt lat="-20" lon="{-44 + i * 0.1 * K:.6f}">' + (f'<ele>{800 + 300 * math.sin(i / 100 * math.pi):.1f}</ele>' if ele else '') + '</trkpt>' for i in range(101))
    return '<?xml version="1.0"?><gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>' + pts + '</trkseg></trk></gpx>'

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        pg = await b.new_page(viewport={'width': 1600, 'height': 720})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
        await pg.goto('http://localhost:8765/index.html?trilha=1'); await pg.wait_for_timeout(1500)
        check('plugins carregados (rotate + elevation)', await pg.evaluate("typeof TN.map.setBearing==='function'&&typeof L.control.elevation==='function'"))

        # ---------- rotação ----------
        await pg.click('[data-pane=paneMap]'); await pg.wait_for_timeout(300)
        await pg.evaluate('()=>{TN.map.setView([-20,-44],15,{animate:false});TN.cfg.rot=true}')
        # rumo 90 (leste): o que está a leste do centro deve aparecer ACIMA do centro na tela
        await pg.evaluate('()=>{TN.onPos({timestamp:1e12,coords:{latitude:-20,longitude:-44,altitude:0,accuracy:5,speed:10,heading:90}});TN.onPos({timestamp:1e12+1000,coords:{latitude:-20,longitude:-43.9999,altitude:0,accuracy:5,speed:10,heading:90}})}')
        await pg.wait_for_timeout(300)
        r = await pg.evaluate('''()=>{const m=TN.map,c=m.getCenter(),e=L.latLng(c.lat,c.lng+0.002),n=L.latLng(c.lat+0.002,c.lng);
          const pc=m.latLngToContainerPoint(c),pe=m.latLngToContainerPoint(e),pn=m.latLngToContainerPoint(n);
          return {bearing:m.getBearing(),leste:[pe.x-pc.x,pe.y-pc.y],norte:[pn.x-pc.x,pn.y-pc.y],seta:document.getElementById('meSvg').style.transform}}''')
        check('bearing = 360 - rumo (270)', abs(((r['bearing'] % 360) + 360) % 360 - 270) < 1, str(r))
        check('rumo para cima: o leste fica em cima do centro', r['leste'][1] < -40 and abs(r['leste'][0]) < 5, str(r['leste']))
        check('o norte vai para a esquerda', r['norte'][0] < -40 and abs(r['norte'][1]) < 5, str(r['norte']))
        ang = float(r['seta'].split('(')[1].split('deg')[0])
        check('seta do "você" aponta para cima (sem dupla rotação)', min(ang % 360, 360 - ang % 360) < 2, r['seta'])
        await pg.screenshot(path='rot.png')
        await pg.evaluate('()=>{TN.cfg.rot=false;TN.applyHeading()}')
        check('rotação desligada volta ao norte para cima', abs(await pg.evaluate('TN.map.getBearing()')) < 0.5)

        # ---------- altimetria ----------
        await pg.evaluate('(x)=>TN.loadGPX(x,"morro.gpx")', gpx(True)); await pg.wait_for_timeout(300)
        await pg.evaluate("document.querySelector('#bElev').click()"); await pg.wait_for_timeout(1500)
        info = await pg.evaluate('''()=>({svg:document.querySelectorAll('#elevDiv svg').length,paths:document.querySelectorAll('#elevDiv path').length,box:document.querySelector('#elevDiv').getBoundingClientRect().height,msg:document.querySelector('#elevMsg').style.display,txt:document.querySelector('#elevDiv').innerText.slice(0,160).replace(/\\n/g,' | '),n:TN.elevCtl&&TN.elevCtl._data&&TN.elevCtl._data.length})''')
        check('perfil desenhado (svg + caminhos + 101 pontos)', info['svg'] >= 1 and info['paths'] >= 2 and info['n'] == 101, str(info))
        await pg.screenshot(path='elev.png')
        # cursor da posição atual no gráfico
        await pg.evaluate('()=>{for(let i=0;i<4;i++)TN.onPos({timestamp:2e12+i*1000,coords:{latitude:-20,longitude:-44+5*0.0095699+i*0.0001,altitude:0,accuracy:5,speed:10,heading:90}})}')
        await pg.wait_for_timeout(200)
        cur = await pg.evaluate('''()=>{const l=document.querySelector('#elevDiv .mouse-focus-line');return l?{x:+l.getAttribute('x1'),w:TN.elevCtl._width(),km:TN.prog&&TN.prog.km}:null}''')
        check('cursor da posição atual no perfil (~ meio do trecho)', cur and 0.35 < cur['x'] / cur['w'] < 0.65, str(cur))
        await pg.screenshot(path='elev2.png')
        await pg.evaluate("document.querySelector('#bElev').click()"); await pg.wait_for_timeout(300)
        check('botão esconde o perfil', await pg.evaluate("!document.querySelector('#paneMap').classList.contains('withElev')"))
        await pg.evaluate('(x)=>TN.loadGPX(x,"sem-ele.gpx")', gpx(False)); await pg.evaluate("document.querySelector('#bElev').click()"); await pg.wait_for_timeout(800)
        msg = await pg.evaluate("document.querySelector('#elevMsg').textContent")
        check('GPX sem altitude: mostra aviso em vez de gráfico vazio', 'não tem altitude' in msg, msg)
        # ---------- mapa vetorial offline com o mapa girado ----------
        await pg.set_input_files('#offIn', 'small.pmtiles'); await pg.wait_for_timeout(3500)
        await pg.evaluate('()=>{TN.map.setView([0,0],2,{animate:false});TN.map.setBearing(45)}'); await pg.wait_for_timeout(1500)
        v = await pg.evaluate('''()=>({tiles:document.querySelectorAll('#map canvas.leaflet-tile').length,bearing:TN.map.getBearing(),info:document.querySelector('#offInfo').textContent.slice(0,40)})''')
        check('mapa offline (vetorial) desenha com o mapa girado a 45°', v['tiles'] > 0 and abs(v['bearing'] - 45) < 1, str(v))
        await pg.screenshot(path='offrot.png')
        check('sem erros de console', not errs, str(errs))
        await b.close()
    print('\nRESULTADO:', 'FALHOU ' + str(FAILS) if FAILS else 'tudo certo')
    sys.exit(1 if FAILS else 0)
asyncio.run(main())
