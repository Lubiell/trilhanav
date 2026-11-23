"""Rotação do mapa (leaflet-rotate), também com o mapa offline vetorial."""
import asyncio, sys
from playwright.async_api import async_playwright

FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        pg = await b.new_page(viewport={'width': 1600, 'height': 720})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
        await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(1500)
        check('leaflet-rotate carregado (e a altimetria não)', await pg.evaluate("typeof TN.map.setBearing==='function'&&typeof L.control.elevation==='undefined'"))

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
        await pg.evaluate('()=>{TN.cfg.rot=false;TN.applyHeading()}')
        check('rotação desligada volta ao norte para cima', abs(await pg.evaluate('TN.map.getBearing()')) < 0.5)

        # ---------- mapa vetorial offline com o mapa girado ----------
        await pg.set_input_files('#offIn', 'small.pmtiles'); await pg.wait_for_timeout(3500)
        await pg.evaluate('()=>{TN.map.setView([0,0],2,{animate:false});TN.map.setBearing(45)}'); await pg.wait_for_timeout(1500)
        v = await pg.evaluate('''()=>({tiles:document.querySelectorAll('#map canvas.leaflet-tile').length,bearing:TN.map.getBearing(),info:document.querySelector('#offInfo').textContent.slice(0,40)})''')
        check('mapa offline (vetorial) desenha com o mapa girado a 45°', v['tiles'] > 0 and abs(v['bearing'] - 45) < 1, str(v))
        check('sem erros de console', not errs, str(errs))
        await b.close()
    print('\nRESULTADO:', 'FALHOU ' + str(FAILS) if FAILS else 'tudo certo')
    sys.exit(1 if FAILS else 0)
asyncio.run(main())
