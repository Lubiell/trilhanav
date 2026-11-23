"""Etapa 1: CAP com bússola do aparelho e correção automática do odômetro pelo roadbook."""
import asyncio, sys
from playwright.async_api import async_playwright

FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

ORIENT = '''([a,b,g])=>{window.dispatchEvent(new DeviceOrientationEvent('deviceorientationabsolute',{alpha:a,beta:b,gamma:g,absolute:true}));TN.applyHeading();return document.querySelector('#hdgTxt').textContent}'''
RESET_COMP = '()=>{TN.comp.mag=null;TN.comp.lastG=null}'
# anda pelo trilho de t.gpx como em t.py (70 km/h) e devolve o TOTAL no instante em que cada waypoint foi validado
DRIVE = '''()=>{const t=Date.now();const out=[];let prev=TN.wpState.map(s=>s);
  for(let i=0;i<=100;i++){const lat=-23.55+i*0.0003*0.99,lon=-46.63+i*0.0002*0.99;
    TN.onPos({timestamp:t+i*2000,coords:{latitude:lat,longitude:lon,altitude:800,accuracy:5,speed:null,heading:null}});
    TN.wpState.forEach((s,k)=>{if(s==='ok'&&prev[k]!=='ok'){out.push({k,total:TN.st.total,km:TN.wps[k].km})}prev[k]=s})}
  return {out,total:TN.st.total,mult:TN.cfg.mult}}'''

async def fresh(b, pg=None):
    ctx = await b.new_context(viewport={'width': 1600, 'height': 720})
    pg = await ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
    await pg.goto('http://localhost:8765/index.html?trilha=1'); await pg.wait_for_timeout(1500)
    await pg.set_input_files('#fileIn', 't.gpx'); await pg.wait_for_timeout(500)
    return pg, errs

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')

        # ---------- km dos waypoints ----------
        pg, errs = await fresh(b)
        kms = await pg.evaluate('TN.wps.map(w=>w.km)')
        check('waypoints ganham km de roadbook, crescentes', all(k is not None for k in kms) and kms == sorted(kms) and kms[0] > 0, str([round(k, 2) for k in kms]))

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
        # a seta de CAP usa o rumo da bússola
        rot = await pg.evaluate('''()=>{TN.updateNav&&0;return document.querySelector('#capArrow').style.transform}''')
        check('seta de CAP girou', 'rotate(' in rot, rot)
        check('sem erros (bússola)', not errs, str(errs))
        await pg.context.close()

        # ---------- correção do odômetro ----------
        pg, errs = await fresh(b)
        await pg.evaluate('TN.cfg.mult=0.95')           # odômetro "andando" 5% a menos
        r = await pg.evaluate(DRIVE)
        ok = [abs(o['total'] - o['km']) < 1e-6 for o in r['out']]
        check('cada waypoint validado alinha o TOTAL ao km do roadbook', len(r['out']) == 3 and all(ok), str(r['out']))
        await pg.context.close()

        pg, errs = await fresh(b)
        await pg.evaluate('()=>{TN.cfg.mult=0.95;TN.cfg.snap=false}')
        r = await pg.evaluate(DRIVE)
        check('com a correção desligada o erro de 5% aparece', len(r['out']) == 3 and abs(r['out'][2]['total'] - r['out'][2]['km']) > 0.15, str(r['out']))
        await pg.context.close()

        pg, errs = await fresh(b)
        await pg.evaluate('()=>{TN.st.total=50}')       # TOTAL sem relação com o roadbook
        await pg.evaluate('()=>{window.__t=[];const o=window.toast;window.toast=(t,ms)=>{window.__t.push(t);o(t,ms)}}')
        r = await pg.evaluate(DRIVE)
        tt = await pg.evaluate('window.__t')
        check('aviso de divergência vem junto do toast de validação, uma vez só', sum('difere' in x for x in tt) == 1 and any('validado' in x and 'difere' in x for x in tt), str([x for x in tt if 'difere' in x][:1]))
        check('TOTAL muito diferente do roadbook: não corrige e avisa', all(o['total'] > 40 for o in r['out']) and await pg.evaluate('TN.snapWarned'), str(r['out']))
        await pg.evaluate("document.querySelector('#bWp').click()"); await pg.wait_for_timeout(200)
        await pg.evaluate("()=>{TN.st.total=50}")
        await pg.evaluate("()=>{document.querySelector('#bPrevWp').click();}")
        await pg.click('#bAlignWp'); await pg.wait_for_timeout(100)
        t = await pg.evaluate('()=>({t:TN.st.total,k:TN.wps[TN.st.wpIdx].km})')
        check('botão "Alinhar TOTAL" força o alinhamento', abs(t['t'] - t['k']) < 1e-6, str(t))
        await pg.context.close()

        pg, errs = await fresh(b)
        await pg.evaluate('()=>{TN.cfg.mult=0.95;TN.cfg.learn=true}')
        await pg.evaluate('()=>{window.__t=[];const o=window.toast;window.toast=(t,ms)=>{window.__t.push(t);o(t,ms)}}')
        r = await pg.evaluate(DRIVE)
        tt = await pg.evaluate('window.__t')
        check('toast de validação informa a correção do odômetro', any('validado' in x and 'odômetro' in x for x in tt), str([x for x in tt if 'odômetro' in x][:1]))
        check('aprender multiplicador: sobe de 0.95 em direção a 1.00', 0.96 < r['mult'] <= 1.0, str(r['mult']))
        check('sem erros (odômetro)', not errs, str(errs))
        await pg.context.close()
        await b.close()
    print('\nRESULTADO:', 'FALHOU ' + str(FAILS) if FAILS else 'tudo certo')
    sys.exit(1 if FAILS else 0)
asyncio.run(main())
