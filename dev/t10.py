"""Etapa 6: rota offline de volta à trilha (roteamento sobre as estradas do mapa offline)."""
import asyncio, sys, math
from playwright.async_api import async_playwright

FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

M_LAT = 111194.9
def m_lon(lat): return M_LAT * math.cos(math.radians(lat))
RIVER = -20.012; BRIDGE = -43.980
STUB = "window.__spk=[];Object.defineProperty(window,'speechSynthesis',{value:{speak:u=>window.__spk.push(u.text),cancel(){},getVoices(){return []}},configurable:true});"

def trail(lat, lon0, lon1):
    n = int(round((lon1 - lon0) / 0.0005))
    pts = ''.join(f'<trkpt lat="{lat}" lon="{lon0 + i * 0.0005:.6f}"/>' for i in range(n + 1))
    return '<?xml version="1.0"?><gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>' + pts + '</trkseg></trk></gpx>'

ONPOS = '''([lat,lon,t])=>TN.onPos({timestamp:t,coords:{latitude:lat,longitude:lon,altitude:0,accuracy:5,speed:0,heading:null}})'''
# dirige ao longo da rota calculada, 54 km/h, e anota o que o app mostra
DRIVE = '''([t0])=>{const rt=TN.rtBack,pts=rt.pts,cum=rt.cum,out={labels:[],caps:[],arrived:false,steps:0};let t=t0,prev=null;
  for(let m=0;m<=rt.len+120;m+=30){let i=0;while(i<pts.length-2&&cum[i+1]<m)i++;const s=cum[i+1]-cum[i],f=s?Math.min(1,Math.max(0,(m-cum[i])/s)):0;
    const lat=pts[i].lat+(pts[i+1].lat-pts[i].lat)*f,lon=pts[i].lon+(pts[i+1].lon-pts[i].lon)*f;
    TN.onPos({timestamp:t,coords:{latitude:lat,longitude:lon,altitude:0,accuracy:5,speed:15,heading:null}});t+=2000;out.steps++;
    if(!TN.rtBack){out.arrived=true;break}
    out.labels.push(document.querySelector('#wpLabel').textContent);out.caps.push(document.querySelector('#cap').textContent)}
  return out}'''

async def newpage(b, offline=True):
    ctx = await b.new_context(viewport={'width': 1600, 'height': 720})
    await ctx.add_init_script(STUB)
    pg = await ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
    await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(1200)
    if offline:
        await pg.set_input_files('#offIn', 'roads.pmtiles'); await pg.wait_for_timeout(3500)
    return pg, errs

def on_grid(lat, lon):
    dl = abs((lat + 20.030) / 0.002 - round((lat + 20.030) / 0.002)) * 0.002 * M_LAT
    dn = abs((lon + 44.020) / 0.002 - round((lon + 44.020) / 0.002)) * 0.002 * m_lon(lat)
    return min(dl, dn) < 4

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')

        # ========== rio com uma ponte: o caminho tem que dar a volta ==========
        pg, errs = await newpage(b)
        check('mapa offline de estradas instalado', 'Instalado' in await pg.text_content('#offInfo'), await pg.text_content('#offInfo'))
        await pg.evaluate('(x)=>TN.loadGPX(x,"trilha-sul.gpx")', trail(-20.020, -44.010, -43.950)); await pg.wait_for_timeout(300)
        t0 = 1_000_000_000_000
        await pg.evaluate(ONPOS, [-20.004, -44.000, t0]); await pg.evaluate(ONPOS, [-20.004, -44.000, t0 + 1000])
        await pg.evaluate("document.querySelector('#bBack').click()"); await pg.wait_for_timeout(2500)
        rt = await pg.evaluate('TN.rtBack&&{mode:TN.rtBack.mode,len:TN.rtBack.len,pts:TN.rtBack.pts,turns:TN.rtBack.turns.length,id:TN.rtBack.id}')
        check('rota calculada sobre o mapa offline (não em linha reta)', rt and rt['mode'] == 'mapa', str(rt and (rt['mode'], round(rt['len']))))
        straight = math.hypot(0.016 * M_LAT, 0)
        check('dá a volta pela ponte: ~3,9 km contra 1,8 km em linha reta', rt and 3600 <= rt['len'] <= 4300, f"{rt['len']:.0f} m (reta {straight:.0f} m)")
        pts = rt['pts']
        cross = [(a, c) for a, c in zip(pts, pts[1:]) if (a['lat'] - RIVER) * (c['lat'] - RIVER) < 0]
        check('atravessa o rio uma vez só, e na ponte (lon -43.980)', len(cross) == 1 and abs(cross[0][0]['lon'] - BRIDGE) < 0.00005 and abs(cross[0][1]['lon'] - BRIDGE) < 0.00005, str([(round(a['lon'], 5), round(c['lon'], 5)) for a, c in cross]))
        inner = pts[1:-1]
        check('todos os vértices da rota estão sobre estradas da malha', all(on_grid(q['lat'], q['lon']) for q in inner), f'{sum(not on_grid(q["lat"], q["lon"]) for q in inner)} fora de {len(inner)}')
        check('começa em você e termina na trilha (lat -20.020)', abs(pts[0]['lat'] + 20.004) < 1e-6 and abs(pts[-1]['lat'] + 20.020) * M_LAT < 8, f"{pts[-1]['lat']:.5f}")
        tx = sorted({int((q['lon'] + 180) / 360 * 2 ** 14) for q in pts}); ty = sorted({int((1 - math.asinh(math.tan(math.radians(q['lat']))) / math.pi) / 2 * 2 ** 14) for q in pts})
        check('a rota cruza limites de tile z14 (a ligação entre tiles funcionou)', len(tx) * len(ty) >= 2, f'tiles x={tx} y={ty}')
        check('há avisos de curva na rota', rt['turns'] >= 2, str(rt['turns']))
        check('rota desenhada no mapa', await pg.evaluate('!!TN.rtLayer') and await pg.evaluate("document.querySelector('#bBack').classList.contains('on')"))
        check('CAP mostra VOLTAR À TRILHA', 'VOLTAR' in await pg.text_content('#wpLabel'), await pg.text_content('#wpLabel'))
        spk = await pg.evaluate('TN.spoken')
        check('copiloto avisa a distância do caminho de volta', any('Caminho de volta à trilha: 3.' in x or 'Caminho de volta à trilha: 4.' in x for x in spk), str(spk))
        # ---- seguindo a rota ----
        d = await pg.evaluate(DRIVE, [t0 + 5000])
        check('seguindo a rota: o rótulo do CAP é "VOLTAR À TRILHA" durante o trajeto', d['labels'] and all('VOLTAR' in x for x in d['labels']), str(set(d['labels'])))
        check('CAP aponta para o ponto da rota logo à frente (leste ~090 no início, depois sul ~180)', d['caps'][2] in ('090°', '089°', '091°', '088°', '092°') or abs(int(d['caps'][2][:3]) - 90) <= 5, str(d['caps'][:3]) + ' ... ' + str(d['caps'][-3:]))
        check('chegando à trilha, a rota é encerrada', d['arrived'] and await pg.evaluate('TN.rtBack') is None, str(d['steps']))
        spk = await pg.evaluate('TN.spoken')
        check('copiloto fala "vire à direita/esquerda" nas curvas e "De volta à trilha" no fim', any('vire à' in x or 'curva à' in x for x in spk) and 'De volta à trilha' in spk, str([x for x in spk if 'vire' in x or 'curva' in x or 'trilha' in x]))
        check('botão volta ao normal', not await pg.evaluate("document.querySelector('#bBack').classList.contains('on')"))
        # ---- recalcula ao sair da rota ----
        await pg.evaluate(ONPOS, [-20.004, -44.000, t0 + 100000]); await pg.evaluate(ONPOS, [-20.004, -44.000, t0 + 101000])
        await pg.evaluate("document.querySelector('#bBack').click()"); await pg.wait_for_timeout(2000)
        id1 = await pg.evaluate('TN.rtBack.id')
        await pg.evaluate(ONPOS, [-20.0075, -44.000, t0 + 125000]); await pg.wait_for_timeout(2000)
        id2 = await pg.evaluate('TN.rtBack&&TN.rtBack.id')
        check('saiu da rota (>80 m): recalcula sozinho a partir da nova posição', id2 and id2 > id1 and abs((await pg.evaluate('TN.rtBack.pts[0].lat')) + 20.0075) < 1e-6, f'{id1} -> {id2}')
        await pg.evaluate("document.querySelector('#bBack').click()"); await pg.wait_for_timeout(200)
        check('tocar de novo no botão cancela o retorno', await pg.evaluate('TN.rtBack') is None)
        # ---- já na trilha ----
        await pg.evaluate(ONPOS, [-20.020, -44.000, t0 + 200000]); await pg.evaluate("document.querySelector('#bBack').click()"); await pg.wait_for_timeout(400)
        check('em cima da trilha: avisa e não traça rota', await pg.evaluate('TN.rtBack') is None and 'já está na trilha' in await pg.text_content('#toast'))
        check('sem erros (rota)', not errs, str(errs))
        await pg.context.close()

        # ========== trilha do mesmo lado: reto pela estrada ==========
        pg, errs = await newpage(b)
        await pg.evaluate('(x)=>TN.loadGPX(x,"trilha-norte.gpx")', trail(-20.000, -44.010, -43.990)); await pg.wait_for_timeout(300)
        await pg.evaluate(ONPOS, [-20.004, -44.000, t0]); await pg.evaluate(ONPOS, [-20.004, -44.000, t0 + 1000])
        await pg.evaluate("document.querySelector('#bBack').click()"); await pg.wait_for_timeout(2000)
        rt = await pg.evaluate('TN.rtBack&&{mode:TN.rtBack.mode,len:TN.rtBack.len}')
        check('trilha 440 m ao norte: caminho de ~440 m pela estrada', rt and rt['mode'] == 'mapa' and 420 <= rt['len'] <= 520, str(rt))
        await pg.context.close()

        # ========== trilho enorme: a rota não pode travar ==========
        pg, errs = await newpage(b)
        n = 50000; lon0, lon1 = -44.010, -43.950
        big = '<?xml version="1.0"?><gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>' + ''.join(f'<trkpt lat="-20.020" lon="{lon0 + (lon1 - lon0) * i / n:.7f}"/>' for i in range(n + 1)) + '</trkseg></trk></gpx>'
        await pg.evaluate('(x)=>TN.loadGPX(x,"gigante.gpx")', big); await pg.wait_for_timeout(1500)
        await pg.evaluate(ONPOS, [-20.004, -44.000, t0]); await pg.evaluate(ONPOS, [-20.004, -44.000, t0 + 1000])
        ms = await pg.evaluate('async()=>{const t=performance.now();await TN.routeBack(false);return performance.now()-t}')
        rt = await pg.evaluate('TN.rtBack&&{mode:TN.rtBack.mode,len:TN.rtBack.len}')
        check('trilho de 50 mil pontos: rota calculada em menos de 4 s', rt and rt['mode'] == 'mapa' and 3600 <= rt['len'] <= 4300 and ms < 4000, f'{ms:.0f} ms {rt}')
        await pg.context.close()

        # ========== sem mapa offline: linha reta ==========
        pg, errs = await newpage(b, offline=False)
        await pg.evaluate('(x)=>TN.loadGPX(x,"trilha-sul.gpx")', trail(-20.020, -44.010, -43.950)); await pg.wait_for_timeout(300)
        await pg.evaluate(ONPOS, [-20.004, -44.000, t0]); await pg.evaluate(ONPOS, [-20.004, -44.000, t0 + 1000])
        await pg.evaluate("document.querySelector('#bBack').click()"); await pg.wait_for_timeout(1200)
        rt = await pg.evaluate('TN.rtBack&&{mode:TN.rtBack.mode,len:TN.rtBack.len}')
        check('sem mapa offline: aponta em linha reta (~1,8 km) e avisa', rt and rt['mode'] == 'reta' and 1700 <= rt['len'] <= 1900 and 'linha reta' in await pg.text_content('#toast'), str(rt))
        d = await pg.evaluate(DRIVE, [t0 + 5000])
        check('em linha reta também guia até a trilha e encerra', d['arrived'], str(d['steps']))
        check('sem erros (reta)', not errs, str(errs))
        await pg.context.close()

        # ========== sem GPX / sem GPS ==========
        pg, errs = await newpage(b, offline=False)
        await pg.evaluate("document.querySelector('#bBack').click()"); await pg.wait_for_timeout(200)
        check('sem GPS: avisa', 'Sem GPS' in await pg.text_content('#toast'))
        await pg.evaluate(ONPOS, [-20.004, -44.000, t0]); await pg.evaluate("document.querySelector('#bBack').click()"); await pg.wait_for_timeout(200)
        check('sem GPX: avisa', 'Carregue um GPX' in await pg.text_content('#toast'))
        await b.close()
    print('\nRESULTADO:', 'FALHOU ' + str(FAILS) if FAILS else 'tudo certo')
    sys.exit(1 if FAILS else 0)
asyncio.run(main())
