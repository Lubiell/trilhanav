"""Bússola do aparelho (rumo parado ou devagar, ajuste aprendido pelo GPS)."""
import asyncio, sys
from playwright.async_api import async_playwright

FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

ORIENT = '''([a,b,g])=>{window.dispatchEvent(new DeviceOrientationEvent('deviceorientationabsolute',{alpha:a,beta:b,gamma:g,absolute:true}));TN.applyHeading();return document.querySelector('#hdgTxt').textContent}'''
RESET_COMP = '()=>{TN.comp.mag=null;TN.comp.lastG=null}'

async def fresh(b, pg=None):
    ctx = await b.new_context(viewport={'width': 1600, 'height': 720})
    pg = await ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
    await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(1500)
    return pg, errs

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')

        pg, errs = await fresh(b)

        # ---------- bússola ----------
        r = await pg.evaluate(ORIENT, [90, 0, 0])
        check('deitado, alpha 90 -> rumo 270', r.startswith('RUMO 270°') and '🧭' in r, r)
        await pg.evaluate(RESET_COMP)
        r = await pg.evaluate(ORIENT, [0, 90, 0])
        check('em pé (suporte de guidão), alpha 0 -> rumo 000', r.startswith('RUMO 000°'), r)
        await pg.evaluate(RESET_COMP)
        r = await pg.evaluate(ORIENT, [270, 90, 0])
        check('em pé, alpha 270 -> rumo 090', r.startswith('RUMO 090°'), r)
        await pg.evaluate(RESET_COMP)
        r = await pg.evaluate(ORIENT, [270, 80, 10])
        h = int(r.split()[1][:3])
        check('em pé inclinado (beta 80, gamma 10) continua perto de 90', abs(h - 90) <= 15, r)
        # evento relativo (sem absolute) deve ser ignorado
        await pg.evaluate(RESET_COMP)
        r = await pg.evaluate('''()=>{window.dispatchEvent(new DeviceOrientationEvent('deviceorientation',{alpha:10,beta:0,gamma:0,absolute:false}));return TN.comp.mag}''')
        check('evento de orientação relativa é ignorado', r is None, str(r))
        # cfg.comp desligada -> não usa bússola
        await pg.evaluate('TN.cfg.comp=false')
        await pg.evaluate(RESET_COMP)
        r = await pg.evaluate(ORIENT, [90, 0, 0])
        check('bússola desligada nos ajustes -> sem 🧭', '🧭' not in r, r)
        await pg.evaluate('TN.cfg.comp=true')

        # GPS prevalece em movimento; bússola aprende o ajuste
        await pg.evaluate('()=>{TN.cfg.compOff=0;TN.cfg.compLearned=false}')
        r = await pg.evaluate('''()=>{TN.comp.mag=null;TN.comp.lastG=null;const t=Date.now();
          window.dispatchEvent(new DeviceOrientationEvent('deviceorientationabsolute',{alpha:250,beta:0,gamma:0,absolute:true})); // bússola: 110° magnético
          for(let i=0;i<6;i++)TN.onPos({timestamp:t+i*2000,coords:{latitude:-23.5,longitude:-46.6+i*0.0003,altitude:0,accuracy:5,speed:11,heading:90}});
          return {txt:document.querySelector('#hdgTxt').textContent,off:TN.cfg.compOff,learned:TN.cfg.compLearned}}''')
        check('a 40 km/h vale o rumo do GPS (090), sem 🧭', r['txt'].startswith('RUMO 090°') and '🧭' not in r['txt'], str(r))
        check('bússola aprendeu o ajuste (~ -20°)', r['learned'] and abs(r['off'] + 20) < 1.5, str(r))
        r = await pg.evaluate('''()=>{const t=Date.now()+60000;TN.onPos({timestamp:t,coords:{latitude:-23.5,longitude:-46.598,altitude:0,accuracy:5,speed:0,heading:null}});
          TN.comp.mag=null;window.dispatchEvent(new DeviceOrientationEvent('deviceorientationabsolute',{alpha:160,beta:0,gamma:0,absolute:true})); // 200° magnético
          TN.applyHeading();return document.querySelector('#hdgTxt').textContent}''')
        check('parado, 200° magnético - 20° de ajuste = 180°', r.startswith('RUMO 180°') and '🧭' in r, r)
        check('sem erros (bússola)', not errs, str(errs))
        await pg.context.close()

        await pg.context.close()
        await b.close()
    print('\nRESULTADO:', 'FALHOU ' + str(FAILS) if FAILS else 'tudo certo')
    sys.exit(1 if FAILS else 0)
asyncio.run(main())
