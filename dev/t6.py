"""Etapa 2: copiloto por voz e zonas de velocidade."""
import asyncio, sys, re
from playwright.async_api import async_playwright

FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

K = 0.0095699  # graus de longitude por km em lat -20
def gpx():
    pts = ''.join(f'<trkpt lat="-20" lon="{-44 + i * 0.1 * K:.6f}"/>' for i in range(101))      # 10 km, pontos a cada 100 m
    w = lambda km, n: f'<wpt lat="-20" lon="{-44 + km * K:.6f}"><name>{n}</name></wpt>'
    return '<?xml version="1.0"?><gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">' + w(1, 'WP1') + w(2, 'VEL 40') + w(3, 'FIM') + w(4, 'WP2') + '<trk><trkseg>' + pts + '</trkseg></trk></gpx>'

STUB = "window.__spk=[];Object.defineProperty(window,'speechSynthesis',{value:{speak:u=>window.__spk.push(u.text),cancel(){window.__cancel=(window.__cancel||0)+1},getVoices(){return []}},configurable:true});"
# anda pelo trilho a v km/h, de km a até km b, 1 fix por segundo; devolve banners e falas por passo
DRIVE = '''([a,b,v,t0])=>{const K=0.0095699,step=v/3.6,out=[];let d=a*1000,t=t0;
  while(d<=b*1000){TN.onPos({timestamp:t,coords:{latitude:-20,longitude:-44+d/1000*K,altitude:0,accuracy:5,speed:v/3.6,heading:90}});
    const bn=document.querySelector('#banner');out.push({km:+(d/1000).toFixed(3),b:bn.style.display==='block'?bn.textContent:'',n:TN.spoken.length});d+=step;t+=1000}
  return out}'''

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        ctx = await b.new_context(viewport={'width': 1600, 'height': 720})
        await ctx.add_init_script(STUB)
        pg = await ctx.new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
        await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(1200)
        await pg.evaluate('(x)=>TN.loadGPX(x,"z.gpx")', gpx()); await pg.wait_for_timeout(300)

        z = await pg.evaluate('TN.zones')
        check('zona criada a partir dos waypoints "VEL 40" ... "FIM"', len(z) == 1 and z[0]['limit'] == 40 and abs(z[0]['from'] - 2) < 0.02 and abs(z[0]['to'] - 3) < 0.02 and z[0]['src'] == 'gpx', str(z))
        ev = await pg.evaluate('TN.events.map(e=>e.kind+":"+e.say)')
        check('eventos: 2 waypoints + 1 zona (marcadores VEL/FIM não viram evento próprio)', sorted(e.split(':')[0] for e in ev) == ['wp', 'wp', 'zone'], str(ev))

        # --- 60 km/h do km 0 ao km 5,2 ---
        t0 = 1_000_000_000_000
        steps = await pg.evaluate(DRIVE, [0.0, 5.2, 60, t0])
        spk = await pg.evaluate('TN.spoken')
        browser_spk = await pg.evaluate('window.__spk')
        check('as falas chegam ao speechSynthesis', spk == browser_spk and len(spk) > 0, str(spk))
        check('fala do waypoint 1 (uma vez, 150-200 m antes)', sum(bool(re.fullmatch(r'Em (150|200) metros, WP1', x)) for x in spk) == 1, str(spk))
        check('aviso antecipado da zona (uma vez)', sum(bool(re.fullmatch(r'Em (150|200) metros, zona de velocidade, limite 40 quilômetros por hora', x)) for x in spk) == 1, str(spk))
        check('aviso do waypoint 2 (uma vez)', sum(bool(re.fullmatch(r'Em (150|200) metros, WP2', x)) for x in spk) == 1, str(spk))
        check('falou "Fim da zona de velocidade" uma vez', spk.count('Fim da zona de velocidade') == 1, str(spk))
        ant = [s for s in steps if s['b'].startswith('ZONA 40 EM')]
        check('banner "ZONA 40 EM … REDUZA" antes da zona, só entre km 1,78 e 2,0', ant and all(1.78 <= s['km'] <= 2.0 for s in ant), str([(s['km'], s['b']) for s in ant][:3]))
        dentro = [s for s in steps if 2.02 <= s['km'] <= 2.98]
        check('dentro da zona a 60 km/h: banner de excesso', all('VELOCIDADE 60 / LIMITE 40' in s['b'] for s in dentro), str(dentro[:1]))
        fora = [s for s in steps if s['km'] >= 3.05 and s['km'] <= 4.7]
        check('depois da zona: sem banner', all(s['b'] == '' for s in fora), str([s for s in fora if s['b']][:2]))
        check('"Velocidade acima do limite" falada uma vez e "Reduza a velocidade" a cada ~12 s', spk.count('Velocidade acima do limite. Limite 40') == 1 and 3 <= spk.count('Reduza a velocidade') <= 5, str([x for x in spk if 'imite' in x or 'Reduza' in x]))
        check('excesso interrompe a fala anterior (urgente)', (await pg.evaluate('window.__cancel||0')) >= 1)

        # --- a 30 km/h dentro da zona não há alerta ---
        await pg.evaluate('()=>{TN.spoken.length=0}')
        steps = await pg.evaluate(DRIVE, [1.5, 3.2, 30, t0 + 100000])
        dentro = [s for s in steps if 2.02 <= s['km'] <= 2.98]
        check('a 30 km/h dentro da zona: sem alerta', all(s['b'] == '' for s in dentro), str(dentro[:1]))

        # --- voltar ao início rearma os avisos ---
        await pg.evaluate('()=>{TN.spoken.length=0}')
        await pg.evaluate(DRIVE, [0.0, 1.0, 40, t0 + 300000])
        spk = await pg.evaluate('TN.spoken')
        await pg.evaluate(DRIVE, [1.0, 1.9, 40, t0 + 400000])
        spk = await pg.evaluate('TN.spoken')
        check('voltando ao início, os avisos são rearmados', any('WP1' in x for x in spk), str(spk))

        # --- voz desligada: registra mas não fala ---
        await pg.evaluate('()=>{TN.cfg.voice=false;window.__spk.length=0;TN.say("teste mudo")}')
        check('voz desligada não chama o speechSynthesis', await pg.evaluate('window.__spk.length') == 0)
        await pg.evaluate('()=>{TN.cfg.voice=true}')

        # --- zona criada à mão pelo diálogo, e persistência ---
        await pg.evaluate("document.querySelector('#bSet').click()"); await pg.click('#bZones'); await pg.wait_for_timeout(200)
        await pg.fill('#zFrom', '6'); await pg.fill('#zTo', '7'); await pg.fill('#zLim', '30'); await pg.click('#zAdd')
        z = await pg.evaluate('TN.zones')
        check('zona manual adicionada', len(z) == 2 and any(q['src'] == 'user' and q['limit'] == 30 for q in z), str(z))
        await pg.fill('#zFrom', '9'); await pg.fill('#zTo', '8'); await pg.click('#zAdd')
        check('zona inválida (fim antes do início) é recusada', len(await pg.evaluate('TN.zones')) == 2)
        await pg.reload(); await pg.wait_for_timeout(1500)
        z = await pg.evaluate('TN.zones')
        check('zonas (GPX + manual) voltam depois de recarregar o app', len(z) == 2, str(z))
        await pg.evaluate("document.querySelector('#bSet').click()"); await pg.click('#bZones'); await pg.wait_for_timeout(200)
        await pg.click('#zList [data-rm]'); await pg.wait_for_timeout(100)
        check('remover zona manual', len(await pg.evaluate('TN.zones')) == 1)
        check('sem erros', not errs, str(errs))
        await b.close()
    print('\nRESULTADO:', 'FALHOU ' + str(FAILS) if FAILS else 'tudo certo')
    sys.exit(1 if FAILS else 0)
asyncio.run(main())
