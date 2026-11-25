"""v2.7.10, a pedido do dono (print da rota): "colocar a janela de direção menor e poder movê-la para outro lugar, e colocar a opção
dela aparecer em segundo plano, pq quando fecha ela, para de dar a direção, e ela fica em cima de outras abas, não pode acontecer".
Cartão compacto (toque abre os detalhes), "–" esconde sem parar a rota (bolinha com a seta), "Sair" pergunta antes, em cima ou
embaixo (⇅ ou arrastar; guardado), só na aba Mapa, notificação com a próxima manobra quando o app vai para segundo plano.
Nativo simulado (o lado Java da notificação só roda no celular/emulador)."""
import asyncio, json, math, os, sys
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html'
FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

FAKE = """
window.__calls=[];window.__ls={};window.__hid=false;localStorage.setItem('tn_updT',String(Date.now()));localStorage.setItem('tn_netOk','true');
Object.defineProperty(document,'hidden',{configurable:true,get:()=>window.__hid});
Object.defineProperty(document,'visibilityState',{configurable:true,get:()=>window.__hid?'hidden':'visible'});
window.__status={phone:true,contacts:true,mic:true,notifAccess:true,speech:true,installAllowed:true,sdk:34,voiceOn:true,notif:{connected:true}};
window.__emit=(ev,d)=>(window.__ls[ev]||[]).forEach(f=>f(d));
const rec=m=>async o=>{__calls.push([m,o||{}])};
window.Capacitor={isNativePlatform:()=>true,getPlatform:()=>'android',registerPlugin:(n)=>({
  addWatcher:async()=>'w1',removeWatcher:rec('removeWatcher'),requestNotifications:async()=>{},speak:rec('speak'),
  addListener:(ev,cb)=>{(__ls[ev]=__ls[ev]||[]).push(cb);return Promise.resolve({remove(){}})},
  phoneStatus:async()=>__status,listContacts:async()=>({list:[]}),
  voiceStart:async o=>{__calls.push(['voiceStart',o])},voiceStop:rec('voiceStop'),voiceBt:rec('voiceBt'),
  navNotify:rec('navNotify'),exitApp:rec('exitApp'),appInfo:async()=>({version:'2.7.10',code:20710})})};
"""
LAT0, LON0 = -19.9200, -43.9400
KLON = 1 / (111194.9 * math.cos(math.radians(LAT0)))
KLAT = 1 / 111194.9
leg1 = [(LAT0, LON0 + i * 20 * KLON) for i in range(31)]
c = leg1[-1]
leg2 = [(c[0] - i * 20 * KLAT, c[1]) for i in range(1, 26)]
PTS = leg1 + leg2
DEST = PTS[-1]

def enc6(pts):
    out, pl, po = [], 0, 0
    for la, lo in pts:
        a, b = round(la * 1e6), round(lo * 1e6)
        for v in (a - pl, b - po):
            v = ~(v << 1) if v < 0 else v << 1
            while v >= 0x20:
                out.append(chr((0x20 | (v & 0x1f)) + 63)); v >>= 5
            out.append(chr(v + 63))
        pl, po = a, b
    return ''.join(out)

def trip(pts):
    n = len(pts)
    man = [{'type': 1, 'instruction': 'Siga para o leste na Rua A.', 'verbal_pre_transition_instruction': 'Siga para o leste na Rua A.', 'street_names': ['Rua A'], 'begin_shape_index': 0, 'end_shape_index': 30, 'length': 0.6, 'time': 50},
           {'type': 10, 'instruction': 'Vire à direita na Rua Astolfo Mendes de Carvalho.', 'verbal_transition_alert_instruction': 'Vire à direita na Rua Astolfo Mendes de Carvalho.',
            'verbal_pre_transition_instruction': 'Vire à direita na Rua Astolfo Mendes de Carvalho.', 'street_names': ['Rua Astolfo Mendes de Carvalho'], 'begin_shape_index': 30, 'end_shape_index': n - 1, 'length': 0.5, 'time': 40},
           {'type': 4, 'instruction': 'Você chegou ao seu destino.', 'verbal_pre_transition_instruction': 'Você chegou ao seu destino.', 'begin_shape_index': n - 1, 'end_shape_index': n - 1, 'length': 0, 'time': 0}]
    return {'legs': [{'shape': enc6(pts), 'maneuvers': man}], 'summary': {'length': 1.1, 'time': 90}}

SHOTS = os.environ.get('SHOTS')   # pasta para os prints (opcional)
async def shot(pg, nome):
    if SHOTS: await pg.screenshot(path=os.path.join(SHOTS, 't31-%s.png' % nome))

FIX = '''([la,lo,v,h,t])=>TN.onPos({timestamp:t,coords:{latitude:la,longitude:lo,altitude:800,accuracy:5,speed:v,heading:h}})'''
START = "TN.navStart(TN.parseTrip(%s),{name:'Tocantins',lat:%f,lon:%f})" % (json.dumps(trip(PTS)), DEST[0], DEST[1])
BOX = "(s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect(),cs=getComputedStyle(e);return {vis:cs.display!=='none'&&r.height>0,top:Math.round(r.top),bot:Math.round(r.bottom),h:Math.round(r.height),cx:Math.round(r.left+r.width/2),cy:Math.round(r.top+r.height/2)}})"
VIEW = "(()=>{const r=document.querySelector('#view').getBoundingClientRect();return {top:Math.round(r.top),bot:Math.round(r.bottom),h:Math.round(r.height)}})()"

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        ctx = await b.new_context(viewport={'width': 360, 'height': 780}, has_touch=False)
        await ctx.add_init_script(FAKE)
        async def route(r):
            u = r.request.url
            if u.endswith('/lib/capacitor.js'): await r.fulfill(status=200, content_type='application/javascript', body=''); return
            if u.startswith('http://localhost') or 'cdnjs.cloudflare.com' in u or 'fonts.g' in u: await r.continue_(); return
            await r.abort()
        await ctx.route('**/*', route)
        pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(URL); await pg.wait_for_timeout(2000)
        box = lambda s: pg.evaluate(BOX + "(%s)" % json.dumps(s))
        t = 1_700_000_000_000

        # ---------- começa a rota: cartão compacto ----------
        await pg.evaluate(START)
        await pg.evaluate(FIX, [PTS[5][0], PTS[5][1], 10, 90, t]); t += 1000
        await pg.wait_for_timeout(400)
        card, view = await box('#navCard'), await pg.evaluate(VIEW)
        det = await pg.evaluate("[getComputedStyle(document.querySelector('#navSub')).display,getComputedStyle(document.querySelector('#navCard .nvb')).display]")
        check('cartão compacto: uma faixa (≤ 75 px) no topo, sem rua/chegada/Sair', card['vis'] and card['h'] <= 75 and card['top'] - view['top'] < 20 and det == ['none', 'none'], '%s %s' % (card, det))
        await shot(pg, 'compacto')

        # ---------- toque abre e fecha os detalhes; a seta repete a instrução ----------
        await pg.mouse.click(card['cx'], card['cy']); await pg.wait_for_timeout(300)
        exp = await pg.evaluate("document.body.classList.contains('navExp')")
        sair = await box('#navEnd')
        check('toque no cartão abre os detalhes (rua, chegada, ⇅ e Sair)', exp and sair['vis'], str(sair))
        await shot(pg, 'aberto')
        await pg.mouse.click(card['cx'], card['cy'] - 10); await pg.wait_for_timeout(300)
        check('outro toque fecha os detalhes', not await pg.evaluate("document.body.classList.contains('navExp')"))
        n0 = await pg.evaluate('TN.spoken.length')
        await pg.evaluate("document.querySelector('#navArr').click()"); await pg.wait_for_timeout(200)
        spk = await pg.evaluate('TN.spoken.slice(-1)[0]')
        check('toque na seta repete a instrução por voz (e não abre o cartão)', await pg.evaluate('TN.spoken.length') > n0 and spk.startswith('Em ') and not await pg.evaluate("document.body.classList.contains('navExp')"), spk)

        # ---------- "–" esconde sem parar a rota ----------
        await pg.evaluate("document.querySelector('#navHide').click()"); await pg.wait_for_timeout(300)
        pill = await box('#navPill'); d0 = await pg.text_content('#navPillDist')
        check('"–" esconde o cartão e deixa a bolinha com a distância', not (await box('#navCard'))['vis'] and pill['vis'] and 'm' in d0, d0)
        n1 = await pg.evaluate('TN.spoken.length')
        for i in range(8, 21, 2):   # anda com o cartão escondido
            await pg.evaluate(FIX, [PTS[i][0], PTS[i][1], 10, 90, t]); t += 1000
        await pg.wait_for_timeout(200); dmeio = await pg.text_content('#navPillDist')
        for i in range(22, 31, 2):   # até perto da curva
            await pg.evaluate(FIX, [PTS[i][0], PTS[i][1], 10, 90, t]); t += 1000
        await pg.wait_for_timeout(300)
        falas = await pg.evaluate('TN.spoken.slice(%d)' % n1)
        check('escondido, a rota continua: a voz avisa a curva', await pg.evaluate('!!TN.nav') and any('Astolfo' in f for f in falas), str(falas))
        check('… e a bolinha acompanha a distância', dmeio != d0 and 'm' in dmeio, d0 + ' -> ' + dmeio)
        await pg.click('#navPill'); await pg.wait_for_timeout(300)
        check('tocar na bolinha traz o cartão de volta', (await box('#navCard'))['vis'] and not (await box('#navPill'))['vis'])

        # ---------- só na aba Mapa ----------
        await pg.evaluate("document.querySelector('#bot [data-pane=\"paneDash\"]').click()"); await pg.wait_for_timeout(400)
        check('na aba Painel o cartão não fica por cima (nem a bolinha)', not (await box('#navCard'))['vis'] and not (await box('#navPill'))['vis'] and await pg.evaluate('!!TN.nav'))
        await shot(pg, 'painel')
        await pg.evaluate("document.querySelector('#bot [data-pane=\"paneMap\"]').click()"); await pg.wait_for_timeout(400)
        check('voltando ao Mapa o cartão aparece', (await box('#navCard'))['vis'])

        # ---------- Sair pergunta antes ----------
        await pg.mouse.click((await box('#navCard'))['cx'], (await box('#navCard'))['cy']); await pg.wait_for_timeout(300)
        await pg.evaluate("document.querySelector('#navEnd').click()"); await pg.wait_for_timeout(300)
        dlg = await pg.evaluate("document.querySelector('#dlgAsk').open")
        check('"Sair" pergunta "Encerrar a rota?" e a rota segue até confirmar', dlg and 'Encerrar a rota' in await pg.text_content('#askT') and await pg.evaluate('!!TN.nav'))
        await pg.evaluate("document.querySelector('#askNo').click()"); await pg.wait_for_timeout(300)
        check('Cancelar: a rota continua', await pg.evaluate('!!TN.nav'))

        # ---------- em cima ou embaixo ----------
        await pg.evaluate("document.querySelector('#navPos').click()"); await pg.wait_for_timeout(300)
        card, view = await box('#navCard'), await pg.evaluate(VIEW)
        check('⇅ leva o cartão para baixo (e guarda)', abs(view['bot'] - card['bot']) < 20 and json.loads(await pg.evaluate("localStorage.getItem('tn_cfg')"))['navPos'] == 'bottom', '%s %s' % (card, view))
        await pg.mouse.click(card['cx'], card['cy']); await pg.wait_for_timeout(300)   # fecha os detalhes
        if await pg.evaluate("document.body.classList.contains('navExp')"):
            await pg.mouse.click(card['cx'], card['cy']); await pg.wait_for_timeout(300)
        rad = await pg.evaluate("(()=>{const r=document.querySelector('#radBox');r.style.display='flex';const b=r.getBoundingClientRect(),c=document.querySelector('#navCard').getBoundingClientRect();r.style.display='';return b.bottom<=c.top+2})()")
        check('embaixo, o aviso de radar fica acima do cartão (não é coberto)', rad)
        await shot(pg, 'embaixo')
        card = await box('#navCard')
        await pg.mouse.move(card['cx'], card['cy']); await pg.mouse.down()
        for y in range(card['cy'], view['top'] + 60, -40):
            await pg.mouse.move(card['cx'], y)
        await pg.mouse.up(); await pg.wait_for_timeout(400)
        card = await box('#navCard')
        check('arrastar para cima leva o cartão para o topo (sem abrir os detalhes)', card['top'] - view['top'] < 20 and not await pg.evaluate("document.body.classList.contains('navExp')")
              and json.loads(await pg.evaluate("localStorage.getItem('tn_cfg')"))['navPos'] == 'top', str(card))
        await pg.evaluate("document.querySelector('#navPos').click()"); await pg.wait_for_timeout(200)   # deixa embaixo
        await pg.evaluate("TN.navStop()"); await pg.reload(); await pg.wait_for_timeout(2000)
        await pg.evaluate(START); await pg.evaluate(FIX, [PTS[5][0], PTS[5][1], 10, 90, t]); t += 1000; await pg.wait_for_timeout(400)
        card, view = await box('#navCard'), await pg.evaluate(VIEW)
        check('a posição fica guardada (abrindo o app de novo a rota começa embaixo)', abs(view['bot'] - card['bot']) < 20, str(card))

        # ---------- segundo plano: notificação com a próxima manobra ----------
        await pg.evaluate("window.__calls=[];window.__hid=true;document.dispatchEvent(new Event('visibilitychange'))"); await pg.wait_for_timeout(300)
        nn = await pg.evaluate("__calls.filter(c=>c[0]==='navNotify').map(c=>c[1])")
        check('app em segundo plano: notificação com a distância e a manobra', nn and 'm · ' in nn[-1].get('title', '') and 'Astolfo' in nn[-1]['title'] + nn[-1].get('text', ''), str(nn[-1:]))
        for i in range(7, 12):
            await pg.evaluate(FIX, [PTS[i][0], PTS[i][1], 10, 90, t]); t += 1000
        nn2 = await pg.evaluate("__calls.filter(c=>c[0]==='navNotify').length")
        check('… atualiza com a distância, no máximo a cada 3 s (sem martelar o Android)', 1 <= nn2 <= 3, str(nn2))
        await pg.evaluate("window.__hid=false;document.dispatchEvent(new Event('visibilitychange'))"); await pg.wait_for_timeout(200)
        check('de volta ao app: a notificação sai (o cartão está na tela)', (await pg.evaluate("__calls.filter(c=>c[0]==='navNotify').slice(-1)[0][1]")) == {'off': True})
        await pg.evaluate("window.__hid=true;document.dispatchEvent(new Event('visibilitychange'))"); await pg.wait_for_timeout(200)
        await pg.evaluate("TN.navStop()"); await pg.wait_for_timeout(200)
        check('rota encerrada em segundo plano: a notificação sai', (await pg.evaluate("__calls.filter(c=>c[0]==='navNotify').slice(-1)[0][1]")) == {'off': True})
        await pg.evaluate("window.__hid=false;document.dispatchEvent(new Event('visibilitychange'))")

        # ---------- celular deitado ----------
        await pg.set_viewport_size({'width': 740, 'height': 360}); await pg.wait_for_timeout(400)
        await pg.evaluate(START); await pg.evaluate(FIX, [PTS[5][0], PTS[5][1], 10, 90, t]); t += 1000; await pg.wait_for_timeout(400)
        card, view = await box('#navCard'), await pg.evaluate(VIEW)
        check('deitado (740×360): cartão compacto ocupa no máximo um quarto da altura', card['vis'] and card['h'] <= view['h'] * 0.25, '%s %s' % (card, view))
        await shot(pg, 'deitado')
        check('sem erros de página', not errs, str(errs[:3]))
        await b.close()
    print('\nRESULTADO:', 'tudo certo' if not FAILS else 'FALHOU ' + str(FAILS))
    sys.exit(1 if FAILS else 0)

asyncio.run(main())
