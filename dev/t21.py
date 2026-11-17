"""v2.6: aviso de queda (SOS), autonomia de combustível, painel personalizável, ícone novo e tema dia mais contrastado.
Nativo simulado (Capacitor fake: impacto, SMS, ligação); o lado nativo de verdade (acelerômetro, SmsManager) só no celular."""
import asyncio, json, math, sys
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html'
FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

FAKE = """
window.__calls=[];window.__ls={};localStorage.setItem('tn_updT',String(Date.now()));
window.__status={phone:true,contacts:true,mic:false,notifAccess:true,speech:true,installAllowed:true,sdk:34,notif:{}};
window.__emit=(ev,d)=>(window.__ls[ev]||[]).forEach(f=>f(d));
const rec=m=>async o=>{__calls.push([m,o||{}])};
window.Capacitor={isNativePlatform:()=>true,getPlatform:()=>'android',registerPlugin:(n)=>({
  addWatcher:async()=>'w1',removeWatcher:async()=>{},requestNotifications:async()=>{},speak:rec('speak'),mediaKey:rec('mediaKey'),
  addListener:(ev,cb)=>{(__ls[ev]=__ls[ev]||[]).push(cb);return Promise.resolve({remove(){}})},
  phoneStatus:async()=>__status,placeCall:rec('placeCall'),listContacts:async()=>({list:[]}),
  crashArm:async o=>{__calls.push(['crashArm',o]);return {sensor:true}},requestSms:async()=>{__calls.push(['requestSms',{}]);return {granted:true}},
  sendSms:async o=>{__calls.push(['sendSms',o]);return {sent:o.numbers.length}},appInfo:async()=>({version:'2.6.0',code:20600})})};
"""
LAT0, LON0 = -19.9200, -43.9400
KLON = 1 / (111194.9 * math.cos(math.radians(LAT0)))
FIX = '''([la,lo,v,h,t])=>TN.onPos({timestamp:t,coords:{latitude:la,longitude:lo,altitude:800,accuracy:5,speed:v,heading:h}})'''

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        ctx = await b.new_context(viewport={'width': 1280, 'height': 720})
        await ctx.add_init_script(FAKE)
        await ctx.route('**/lib/capacitor.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=''))
        pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(URL); await pg.wait_for_timeout(1500)
        calls = lambda m: pg.evaluate('(m)=>__calls.filter(c=>c[0]===m).map(c=>c[1])', m)
        spoken = lambda: pg.evaluate('TN.spoken.slice()')
        state = {'t': 9_000_000, 'x': 0}
        async def ride(v, n=1, step=None):
            for _ in range(n):
                state['x'] += (v / 3.6 if step is None else step)
                await pg.evaluate(FIX, [LAT0, LON0 + state['x'] * KLON, v / 3.6, 90, state['t']]); state['t'] += 1000

        # ---------- configuração do SOS ----------
        check('desligado por padrão: o sensor não é ligado ao abrir', not await calls('crashArm'))
        await pg.click('#bPhone'); await pg.wait_for_timeout(400)
        await pg.fill('#sosNm', 'Ana'); await pg.fill('#sosNum', '(31) 99999-0001'); await pg.click('#sosAdd')
        await pg.fill('#sosNm', 'Beto'); await pg.fill('#sosNum', '31988880002'); await pg.click('#sosAdd')
        await pg.fill('#sCrashName', 'Jefferson'); await pg.dispatch_event('#sCrashName', 'change')
        await pg.click('#sCrashOn'); await pg.wait_for_timeout(300)
        arm = await calls('crashArm')
        check('ligar o aviso: pede permissão de SMS e liga o sensor com 4 g', len(await calls('requestSms')) == 1 and arm and arm[-1] == {'on': True, 'g': 4}, str(arm))
        await pg.select_option('#sCrashSens', 'alta'); await pg.wait_for_timeout(100)
        check('sensibilidade alta → 3 g', (await calls('crashArm'))[-1] == {'on': True, 'g': 3})
        check('contatos de emergência na lista (2)', await pg.evaluate("document.querySelectorAll('#sosList [data-sosrm]').length") == 2)
        await pg.evaluate("document.querySelector('#dlgPhone').close()")

        # ---------- não dispara: parado, devagar, voltou a andar ----------
        await ride(0, 3, step=0)
        await pg.evaluate("TN.onImpact({g:5})")
        check('impacto com a moto parada (tombo) não dispara', await pg.evaluate("TN.sos") is None)
        await ride(15, 6)
        await pg.evaluate("TN.onImpact({g:5})")
        check('impacto a 15 km/h não dispara', await pg.evaluate("TN.sos") is None)
        await ride(40, 6)
        await pg.evaluate("TN.onImpact({g:5})")
        check('impacto a 40 km/h: fica observando (não alarma na hora)', (await pg.evaluate("TN.sos&&TN.sos.phase")) == 'watch' and not await pg.is_visible('#sosBox'))
        await ride(30, 2)
        check('… voltou a andar: não era queda, esquece', await pg.evaluate("TN.sos") is None)

        # ---------- queda: parado 15 s → contagem → cancelar por toque ----------
        await pg.evaluate("TN.cfg.crashSens='normal'")
        await ride(45, 6)
        await pg.evaluate("TN.onImpact({g:6})")
        for _ in range(3): await ride(0, 1, step=0)
        await pg.wait_for_timeout(15400)
        r = await pg.evaluate("({ph:TN.sos&&TN.sos.phase,on:document.querySelector('#sosBox').classList.contains('on'),n:document.querySelector('#sosN').textContent,msg:document.querySelector('#sosMsg').textContent})")
        check('impacto a 45 km/h + parado 15 s: tela vermelha com contagem de 30 s', r['ph'] == 'count' and r['on'] and int(r['n']) in (29, 30) and 'Ana, Beto' in r['msg'], str(r))
        check('voz: "Queda detectada. Diga cancelar…"', (await spoken())[-1].startswith('Queda detectada'))
        await pg.click('#sosOk'); await pg.wait_for_timeout(200)
        check('"Estou bem" cancela: nada enviado', not await pg.is_visible('#sosBox') and not await calls('sendSms') and (await spoken())[-1] == 'Aviso cancelado')

        # ---------- cancelar por voz e por tecla ----------
        for modo in ('voz', 'tecla'):
            await ride(45, 6); await pg.evaluate("TN.onImpact({g:6})")
            for _ in range(2): await ride(0, 1, step=0)
            await pg.wait_for_timeout(15300)
            if modo == 'voz':
                await pg.evaluate("TN.runCmd(TN.parseCmd('estou bem'))")
            else:
                await pg.keyboard.press('PageDown')
            await pg.wait_for_timeout(200)
            check(f'cancelar por {modo} ("estou bem" / tecla do guidão)', await pg.evaluate("TN.sos") is None and not await calls('sendSms'))

        # ---------- sem resposta: SMS + ligação ----------
        await ride(45, 6); await pg.evaluate("TN.onImpact({g:6})")
        for _ in range(2): await ride(0, 1, step=0)
        await pg.wait_for_timeout(15300)
        await pg.evaluate("TN.sos.left=2"); await pg.wait_for_timeout(2600)
        sm = await calls('sendSms')
        txt = sm[-1]['text'] if sm else ''
        check('sem resposta: SMS para os 2 contatos com nome, hora e link do mapa', sm and sm[-1]['numbers'] == ['(31) 99999-0001', '31988880002'] and txt.startswith('TrilhaNav: possível queda de Jefferson às ') and 'https://maps.google.com/?q=-19.92' in txt, txt)
        check('tela mostra "Aviso enviado"', 'Aviso enviado' in await pg.text_content('#sosMsg'))
        await pg.wait_for_timeout(4300)
        check('4 s depois, ainda parado: liga para o 1º contato', (await calls('placeCall')) == [{'number': '31999990001'}], str(await calls('placeCall')))
        await pg.click('#sosOk')

        # ---------- teste pelo botão ----------
        await pg.click('#bPhone'); await pg.wait_for_timeout(300)
        await pg.click('#sosTestB'); await pg.wait_for_timeout(300)
        check('Testar: contagem de 10 s com "TESTE"', await pg.text_content('#sosT') == 'TESTE DO AVISO DE QUEDA' and await pg.text_content('#sosN') == '10' and not await pg.evaluate("document.querySelector('#dlgPhone').open"))
        await pg.evaluate("TN.sos.left=1"); await pg.wait_for_timeout(1500)
        sm = await calls('sendSms')
        check('teste manda SMS dizendo que é teste e NÃO liga', sm[-1]['text'].startswith('TrilhaNav: TESTE do aviso de queda') and len(await calls('placeCall')) == 1)
        await pg.click('#sosOk')

        # ---------- autonomia ----------
        await pg.evaluate("document.querySelector('#bMore').click()"); await pg.wait_for_timeout(150)
        await pg.click('#moreGrid #bFuel'); await pg.wait_for_timeout(300)
        if await pg.evaluate("document.querySelector('#dlgAsk').open"):
            await pg.click('#askNo'); await pg.wait_for_timeout(200)
        check('Combustível abre mesmo sem aceitar a internet (autonomia é offline)', await pg.evaluate("document.querySelector('#dlgFuel').open") and 'precisa de internet' in await pg.text_content('#fuelInfo'))
        for sel, v in (('#sTankL', '10'), ('#sKmL', '20'), ('#sReserveKm', '40')):
            await pg.fill(sel, v); await pg.dispatch_event(sel, 'change')
        await pg.click('#bFilled'); await pg.wait_for_timeout(100)
        check('tanque 10 L × 20 km/l = 200 km; "Abasteci" zera', (await pg.text_content('#rangeInfo')).startswith('200 km restantes') and (await spoken())[-1] == 'Tanque cheio. Autonomia de 200 quilômetros')
        await pg.evaluate("document.querySelector('#dlgFuel').close()")
        await pg.evaluate("(km)=>{TN.fillUp();}", 0)
        await pg.evaluate("(()=>{})()")
        n0 = len(await spoken())
        for _ in range(170):   # ~161 km de uma vez: 0,95 km por passo a 3420 km/h é demais para o filtro; anda em passos de 950 m a cada 30 s
            state['x'] += 950
            await pg.evaluate(FIX, [LAT0, LON0 + state['x'] * KLON, 31.6, 90, state['t']]); state['t'] += 30000
        r = await pg.evaluate("Math.round(TN.rangeKm())")
        sp = (await spoken())[n0:]
        check('rodou ~161 km: autonomia ~39 km e aviso de reserva por voz', 36 <= r <= 42 and any(x.startswith('Reserva de combustível: faltam cerca de') for x in sp), f'{r} {sp[-2:]}')
        check('"Trilha, autonomia" fala o que resta', await pg.evaluate("(()=>{TN.runCmd(TN.parseCmd('autonomia'));return TN.spoken.slice(-1)[0]})()") == f'Autonomia de {r} quilômetros')
        await pg.evaluate("TN.runCmd(TN.parseCmd('abasteci'))")
        check('"Trilha, abasteci" zera a contagem', await pg.evaluate("Math.round(TN.rangeKm())") == 200)

        # ---------- painel personalizável ----------
        await pg.evaluate("document.querySelector('[data-pane=paneDash]').click()"); await pg.wait_for_timeout(200)
        n_all = await pg.evaluate("document.querySelectorAll('#dash .card').length")
        check('Painel mostra todos os mostradores por padrão, inclusive Autonomia e Clima', n_all == await pg.evaluate("TN.DASH.length") and 'AUTONOMIA' in await pg.text_content('#dash'))
        await pg.click('#dashEdit'); await pg.wait_for_timeout(200)
        for k in ('coord', 'recn', 'corr', 'acc'):
            await pg.click(f'#dashItems [data-dk="{k}"]')
        await pg.click('#dashBig'); await pg.evaluate("document.querySelector('#dlgDash').close()"); await pg.wait_for_timeout(200)
        r = await pg.evaluate("({n:document.querySelectorAll('#dash .card').length,big:document.querySelector('#dash').classList.contains('big'),txt:document.querySelector('#dash').textContent})")
        check('Personalizar: tira 4 mostradores e liga os grandes', r['n'] == n_all - 4 and r['big'] and 'COORDENADAS' not in r['txt'], str(r)[:120])
        await pg.reload(); await pg.wait_for_timeout(1200)
        await pg.evaluate("document.querySelector('[data-pane=paneDash]').click()"); await pg.wait_for_timeout(200)
        check('a escolha fica guardada depois de reabrir', await pg.evaluate("document.querySelectorAll('#dash .card').length") == n_all - 4 and await pg.evaluate("document.querySelector('#dash').classList.contains('big')"))

        # ---------- ícone e tema dia ----------
        r = await pg.evaluate("(async()=>{const t=await (await fetch('icon.svg')).text();return {trilha:t.includes('stroke-dasharray'),seta:t.includes('#1e9be0')}})()")
        check('ícone novo (trilha tracejada + seta azul)', r == {'trilha': True, 'seta': True})
        await pg.evaluate("document.body.classList.add('day')")
        c = await pg.evaluate("getComputedStyle(document.body).getPropertyValue('--mut').trim()")
        check('tema dia com texto secundário mais escuro (contraste ao sol)', c == '#2f4355', c)
        await pg.set_viewport_size({'width': 360, 'height': 780}); await pg.wait_for_timeout(300)
        await pg.screenshot(path='/tmp/claude-0/-home-user/51ac65f6-457e-5d09-b14e-b860846fbcdb/scratchpad/png/t21_dia.png')
        await pg.evaluate("document.body.classList.remove('day');TN.onImpact&&0")
        check('sem erros de página', not errs, str(errs[:3]))
        await b.close()
    print('\nRESULTADO:', 'tudo certo' if not FAILS else 'FALHAS: ' + '; '.join(FAILS))
    sys.exit(1 if FAILS else 0)

asyncio.run(main())
