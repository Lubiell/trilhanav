"""v2.6.2: "Ir para" sem Waze/Google Maps e sem internet (rota pelo mapa offline, toque longo no mapa),
fallback quando o Valhalla falha, música (trocar/volume no guidão) e voz (teste com diagnóstico, saída pelo fone)."""
import asyncio, sys
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html'
FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

RIVER = -20.012; BRIDGE = -43.980
STUB = "window.__spk=[];Object.defineProperty(window,'speechSynthesis',{value:{speak:u=>window.__spk.push(u.text),cancel(){},getVoices(){return []}},configurable:true});"
NATIVE = """window.__calls=[];window.__ls={};window.Capacitor={isNativePlatform:()=>true,getPlatform:()=>'android',registerPlugin:(n)=>new Proxy({},{get:(o,k)=>{
  if(k==='then')return undefined;
  if(k==='addListener')return (ev,cb)=>{(__ls[ev]=__ls[ev]||[]).push(cb);return Promise.resolve({remove(){}})};
  if(k==='ttsStatus')return async()=>{__calls.push(['ttsStatus',{}]);return {ready:true,failed:false,langOk:window.__langOk!==false,headset:!!window.__hs}};
  if(k==='phoneStatus'||k==='requestPhone')return async()=>({phone:true,contacts:true,mic:true,notifAccess:false,speech:true});
  if(k==='appInfo')return async()=>({version:'2.6.2',code:20602});
  if(k==='addWatcher')return async()=>'w1';
  return async o=>{__calls.push([k,o||{}]);return {}}}})};"""
ONPOS = '''([lat,lon,t])=>TN.onPos({timestamp:t,coords:{latitude:lat,longitude:lon,altitude:0,accuracy:5,speed:0,heading:null}})'''
DRIVE = '''([t0])=>{const rt=TN.nav.rt,pts=rt.pts,cum=rt.cum,out={arrived:false};let t=t0;
  for(let m=0;m<=rt.len+120;m+=25){let i=0;while(i<pts.length-2&&cum[i+1]<m)i++;const s=cum[i+1]-cum[i],f=s?Math.min(1,Math.max(0,(m-cum[i])/s)):0;
    TN.onPos({timestamp:t,coords:{latitude:pts[i].lat+(pts[i+1].lat-pts[i].lat)*f,longitude:pts[i].lon+(pts[i+1].lon-pts[i].lon)*f,altitude:0,accuracy:5,speed:12,heading:null}});t+=2000;
    if(TN.nav&&TN.nav.arrived){out.arrived=true;break}}
  return out}'''

async def newpage(b, init, offline=True, valhalla=None):
    ctx = await b.new_context(viewport={'width': 1280, 'height': 720})
    await ctx.add_init_script(init + ";localStorage.setItem('tn_updT',String(Date.now()));")
    # sem internet de verdade: tudo fora do localhost falha (o Valhalla pode responder erro se pedido)
    async def net(route):
        u = route.request.url
        if u.startswith('http://localhost') or 'cdnjs.cloudflare.com' in u or 'fonts.g' in u: await route.continue_(); return
        if valhalla is not None and 'valhalla' in u:
            valhalla.append(u); await route.fulfill(status=503, headers={'Access-Control-Allow-Origin': '*'}, body='{"error":"fora do ar"}'); return
        await route.abort()
    await ctx.route('**/*', net)
    await ctx.route('**/lib/capacitor.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=''))
    pg = await ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.goto(URL); await pg.wait_for_timeout(1500)
    if offline:
        await pg.set_input_files('#offIn', 'roads.pmtiles'); await pg.wait_for_timeout(3500)
    return pg, errs

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        src = open('../index.html', encoding='utf-8').read()
        check('sem Waze nem Google Maps no "Ir para"', 'waze' not in src.lower().replace('tipo waze', '').replace('como no waze', '') and 'Abrir no Google Maps' not in src and 'navWaze' not in src)

        # ===== sem internet: toque longo no mapa → rota pelo mapa offline =====
        pg, errs = await newpage(b, STUB)
        t0 = 1_000_000_000_000
        await pg.evaluate(ONPOS, [-20.004, -44.000, t0]); await pg.evaluate(ONPOS, [-20.004, -44.000, t0 + 1000])
        await pg.evaluate("TN.map.fire('contextmenu',{latlng:L.latLng(-20.024,-44.000)})"); await pg.wait_for_timeout(3500)
        await pg.evaluate("document.querySelectorAll('#dlgAsk[open]').forEach(d=>d.close())")  # aviso de internet: recusado
        await pg.wait_for_timeout(300)
        check('toque longo abre o "Ir para" com o ponto do mapa', await pg.evaluate("document.querySelector('#dlgNav').open") and await pg.input_value('#navQ') == 'Ponto no mapa')
        plan = await pg.evaluate("TN.navPlan&&{n:TN.navPlan.routes.length,off:TN.navPlan.routes[0].offline,len:TN.navPlan.routes[0].len,via:TN.navPlan.routes[0].via,pts:TN.navPlan.routes[0].pts,man:TN.navPlan.routes[0].man.map(m=>m.txt)}")
        check('rota calculada pelo mapa offline, sem internet', plan and plan['off'] and 5800 <= plan['len'] <= 6900, str(plan and (plan['len'], plan['via'])))
        cross = [(a, c) for a, c in zip(plan['pts'], plan['pts'][1:]) if (a['lat'] - RIVER) * (c['lat'] - RIVER) < 0]
        check('a rota offline atravessa o rio pela ponte', len(cross) == 1 and abs(cross[0][0]['lon'] - BRIDGE) < 0.00005)
        check('manobras: poucas curvas (sem zigue-zague na malha) e chegada', 2 <= len(plan['man']) - 2 <= 5 and plan['man'][-1] == 'Destino', str(plan['man']))
        await pg.evaluate("document.querySelector('#navRoutes [data-go=\"0\"]').click()"); await pg.wait_for_timeout(500)
        check('rota iniciada no cartão de navegação', await pg.evaluate("!!TN.nav&&TN.nav.rt.offline"))
        d = await pg.evaluate(DRIVE, [t0 + 5000]); await pg.wait_for_timeout(300)
        spk = await pg.evaluate('TN.spoken.slice()')
        check('voz curva a curva e chegada, sem internet', d['arrived'] and 'Você chegou ao destino' in spk and any('à direita' in x or 'à esquerda' in x for x in spk), str(spk[-5:]))
        check('sem erros (offline)', not errs, str(errs))

        # destino longe demais e sem mapa: mensagem certa e opção de linha reta
        await pg.wait_for_timeout(6500)
        await pg.evaluate(ONPOS, [-20.004, -44.000, t0 + 900000])
        await pg.evaluate("TN.map.fire('contextmenu',{latlng:L.latLng(-22.0,-46.0)})"); await pg.wait_for_timeout(1500)
        await pg.evaluate("document.querySelectorAll('#dlgAsk[open]').forEach(d=>d.close())"); await pg.wait_for_timeout(300)
        txt = await pg.text_content('#navRoutes')
        check('longe demais: explica e oferece linha reta', 'longe demais' in txt and await pg.evaluate("!!document.querySelector('#navStraight')"), txt)
        await pg.evaluate("document.querySelector('#navStraight').click()"); await pg.wait_for_timeout(300)
        check('linha reta inicia a rota (bússola)', await pg.evaluate("!!TN.nav&&TN.nav.rt.straight"))

        # ===== com internet aceita, mas o Valhalla falha: cai para o mapa offline =====
        vh = []
        pg, errs = await newpage(b, STUB + "localStorage.setItem('tn_netOk','true');", valhalla=vh)
        await pg.evaluate(ONPOS, [-20.004, -44.000, t0]); await pg.evaluate(ONPOS, [-20.004, -44.000, t0 + 1000])
        await pg.evaluate("TN.map.fire('contextmenu',{latlng:L.latLng(-20.024,-44.000)})"); await pg.wait_for_timeout(5000)
        check('Valhalla fora do ar: usa a rota do mapa offline', len(vh) >= 1 and await pg.evaluate("TN.navPlan&&TN.navPlan.routes[0].offline"), f'valhalla={len(vh)}')
        check('sem erros (fallback)', not errs, str(errs))

        # ===== APK simulado: música e voz =====
        pg, errs = await newpage(b, NATIVE, offline=False)
        check('"Trilha, trocar música" vira próxima', await pg.evaluate("TN.parseCmd('trocar música')&&TN.parseCmd('trocar música').a") == 'next')
        check('"pausar música" pausa', await pg.evaluate("TN.parseCmd('pausar música').a") == 'pause')
        acts = await pg.evaluate("(()=>{const s=document.body.innerHTML;return s})()")
        await pg.evaluate("document.querySelector('#bVoiceTest').click()"); await pg.wait_for_timeout(300)
        names = await pg.evaluate("__calls.map(c=>c[0])")
        check('Testar voz: fala no TTS nativo e confere a voz', 'speak' in names and 'ttsStatus' in names and 'installVoice' not in names, str(names[-6:]))
        await pg.evaluate("window.__hs=true;document.querySelector('#bVoiceTest').click()"); await pg.wait_for_timeout(300)
        check('com o fone do capacete, avisa que sai pelo fone', 'fone do capacete' in await pg.text_content('#toast'), await pg.text_content('#toast'))
        await pg.evaluate("window.__hs=false;window.__langOk=false;document.querySelector('#bVoiceTest').click()"); await pg.wait_for_timeout(300)
        check('sem voz em português: abre a instalação', 'installVoice' in await pg.evaluate("__calls.map(c=>c[0])"))
        check('sem erros (APK)', not errs, str(errs))
        await b.close()
    print('\nRESULTADO:', 'tudo certo' if not FAILS else 'FALHOU ' + str(FAILS))
    sys.exit(1 if FAILS else 0)

asyncio.run(main())
