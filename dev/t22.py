"""v2.6: ligação pelo WhatsApp (notificação de chamada lida pelo acesso a notificações): quem liga, atender/recusar/desligar
por voz e por botão, sem misturar com a ligação comum. Nativo simulado; a notificação real do WhatsApp só no celular."""
import asyncio, sys
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html'
FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

FAKE = """
window.__calls=[];window.__ls={};localStorage.setItem('tn_updT',String(Date.now()));
window.__emit=(ev,d)=>(window.__ls[ev]||[]).forEach(f=>f(d));
const rec=m=>async o=>{__calls.push([m,o||{}])};
window.Capacitor={isNativePlatform:()=>true,getPlatform:()=>'android',registerPlugin:(n)=>({
  addWatcher:async()=>'w1',removeWatcher:async()=>{},requestNotifications:async()=>{},speak:rec('speak'),
  addListener:(ev,cb)=>{(__ls[ev]=__ls[ev]||[]).push(cb);return Promise.resolve({remove(){}})},
  phoneStatus:async()=>({phone:true,contacts:true,mic:true,notifAccess:true,sdk:34,notif:{}}),listContacts:async()=>({list:[]}),
  voiceStart:async()=>{setTimeout(()=>__emit('voice',{state:'on'}),30)},voiceWords:async()=>{},
  answerCall:rec('answerCall'),endCall:rec('endCall'),waCallAction:rec('waCallAction'),appInfo:async()=>({version:'2.6.0',code:20600})})};
"""

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        ctx = await b.new_context(viewport={'width': 360, 'height': 780})
        await ctx.add_init_script(FAKE)
        await ctx.route('**/lib/capacitor.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=''))
        pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(URL); await pg.wait_for_timeout(2200)
        calls = lambda m: pg.evaluate('(m)=>__calls.filter(c=>c[0]===m).map(c=>c[1])', m)
        on = lambda: pg.evaluate("document.querySelector('#callBox').classList.contains('on')")

        # ---------- chamada de voz do WhatsApp: atender pela tela (atender por voz saiu na v2.7.4) ----------
        await pg.evaluate("__emit('wacall',{state:'ringing',name:'Maria Souza',video:false,app:'WhatsApp'})"); await pg.wait_for_timeout(200)
        r = await pg.evaluate("({who:document.querySelector('#callWho').textContent,st:document.querySelector('#callSt').textContent})")
        check('WhatsApp tocando: tela com o nome e "WhatsApp · Ligação chegando"', await on() and r['who'] == 'Maria Souza' and r['st'].startswith('WhatsApp · Ligação chegando'), str(r))
        sp = await pg.evaluate("TN.spoken.slice(-1)[0]")
        check('voz: "Ligação de WhatsApp de Maria Souza. Diga atender ou recusar"', sp == 'Ligação de WhatsApp de Maria Souza. Diga atender ou recusar', sp)
        await pg.evaluate("__emit('heard',{text:'atender'})"); await pg.wait_for_timeout(200)
        check('"atender" por voz (2.7.11) aciona o Atender do WhatsApp, não o do telefone', (await calls('waCallAction')) == [{'act': 'answer'}] and not await calls('answerCall'))
        await pg.click('#callAns'); await pg.wait_for_timeout(100)
        check('Atender da tela também aciona o do WhatsApp', (await calls('waCallAction')) == [{'act': 'answer'}, {'act': 'answer'}] and not await calls('answerCall'))
        await pg.evaluate("__emit('wacall',{state:'offhook',name:'Maria Souza',video:false,app:'WhatsApp'})"); await pg.wait_for_timeout(100)
        r = await pg.evaluate("({b:document.querySelector('#callEnd').textContent,st:document.querySelector('#callSt').textContent})")
        check('em ligação pelo WhatsApp: botão Desligar', r['b'] == 'Desligar' and 'Em ligação' in r['st'], str(r))
        await pg.click('#callEnd'); await pg.wait_for_timeout(100)
        check('Desligar aciona o "desligar" do WhatsApp', (await calls('waCallAction'))[-1] == {'act': 'hangup'})
        await pg.evaluate("__emit('wacall',{state:'idle'})"); await pg.wait_for_timeout(100)
        check('notificação da chamada sumiu: tela fecha', not await on())

        # ---------- chamada de vídeo: recusar ----------
        await pg.evaluate("__emit('wacall',{state:'ringing',name:'João',video:true,app:'WhatsApp Business'})"); await pg.wait_for_timeout(200)
        r = await pg.evaluate("({st:document.querySelector('#callSt').textContent,sp:TN.spoken.slice(-1)[0]})")
        check('vídeo do WhatsApp Business: aparece e é anunciada como chamada de vídeo', r['st'].startswith('WhatsApp Business (vídeo) · ') and r['sp'].startswith('Chamada de vídeo do WhatsApp de João'), str(r))
        await pg.click('#callEnd'); await pg.wait_for_timeout(100)
        check('Recusar da tela aciona o Recusar do WhatsApp', (await calls('waCallAction'))[-1] == {'act': 'decline'} and not await calls('endCall'))
        await pg.evaluate("__emit('wacall',{state:'idle'})")

        # ---------- ligação comum continua com o telefone ----------
        await pg.evaluate("__emit('call',{state:'ringing',number:'+5531999990000',name:'Pedro'})"); await pg.wait_for_timeout(200)
        check('ligação comum depois: tela sem "WhatsApp" e anúncio normal', not (await pg.text_content('#callSt')).startswith('WhatsApp') and (await pg.evaluate("TN.spoken.slice(-1)[0]")).startswith('Ligação de Pedro'))
        await pg.click('#callAns'); await pg.wait_for_timeout(100)
        check('… e Atender usa o telefone', len(await calls('answerCall')) == 1 and len(await calls('waCallAction')) == 4)
        await pg.evaluate("__emit('call',{state:'idle'})")
        check('sem erros de página', not errs, str(errs[:3]))
        await b.close()
    print('\nRESULTADO:', 'tudo certo' if not FAILS else 'FALHAS: ' + '; '.join(FAILS))
    sys.exit(1 if FAILS else 0)

asyncio.run(main())
