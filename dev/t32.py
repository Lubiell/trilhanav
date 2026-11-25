"""v2.7.11 (spec docs/specs/2026-11-25-voz-ligacoes-whatsapp.md, aprovada pelo dono): "Trilha" mais sensível e WhatsApp lendo o texto
só das pessoas escolhidas. ("atender/recusar por voz enquanto toca" está no t26, t18 e t22.)
- "Trilha" vale em qualquer das 3 hipóteses do Vosk; a espera pelo comando depois de "Trilha" sozinho é de 8 s.
- Sensibilidade "alta": aceita "trilho"/"trilhas", põe essas palavras na gramática e liga o reforço do microfone (voiceSens); "normal" não.
- WhatsApp: escolhidos (☆ na mensagem ou pelo nome) têm o texto lido; os outros seguem o ajuste; lista só no aparelho, sem rede.
Nativo simulado."""
import asyncio, json, sys
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html'
FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

FAKE = """
window.__calls=[];window.__ls={};localStorage.setItem('tn_updT',String(Date.now()));
window.__status={phone:true,contacts:true,mic:true,notifAccess:true,speech:true,installAllowed:true,sdk:34,voiceOn:true,notif:{connected:true}};
window.__emit=(ev,d)=>(window.__ls[ev]||[]).forEach(f=>f(d));
const rec=m=>async o=>{__calls.push([m,o||{}])};
window.Capacitor={isNativePlatform:()=>true,getPlatform:()=>'android',registerPlugin:(n)=>({
  addWatcher:async()=>'w1',removeWatcher:async()=>{},requestNotifications:async()=>{},speak:rec('speak'),mediaKey:rec('mediaKey'),
  addListener:(ev,cb)=>{(__ls[ev]=__ls[ev]||[]).push(cb);return Promise.resolve({remove(){}})},
  answerCall:rec('answerCall'),endCall:rec('endCall'),volume:rec('volume'),spotifyPlay:rec('spotifyPlay'),
  phoneStatus:async()=>__status,requestPhone:async()=>__status,listContacts:async()=>({list:[]}),
  voiceStart:async o=>{__calls.push(['voiceStart',o]);setTimeout(()=>__emit('voice',{state:'on'}),50)},voiceStop:rec('voiceStop'),
  voiceWords:rec('voiceWords'),voiceBt:rec('voiceBt'),voiceSens:rec('voiceSens'),navNotify:rec('navNotify'),
  appInfo:async()=>({version:'2.7.11',code:20711})})};
"""

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        ctx = await b.new_context(viewport={'width': 412, 'height': 900})
        await ctx.add_init_script(FAKE)
        reqs = []
        async def route(r):
            u = r.request.url; reqs.append(u)
            if u.endswith('/lib/capacitor.js'): await r.fulfill(status=200, content_type='application/javascript', body=''); return
            if u.startswith('http://localhost') or 'cdnjs.cloudflare.com' in u or 'fonts.g' in u: await r.continue_(); return
            await r.abort()
        await ctx.route('**/*', route)
        pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(URL); await pg.wait_for_timeout(2200)
        calls = lambda m: pg.evaluate("(m)=>__calls.filter(c=>c[0]===m).map(c=>c[1])", m)
        heard = lambda t, alts=None: pg.evaluate("([t,a])=>TN.onHeard(a?{text:t,alts:a}:{text:t})", [t, alts])
        last_log = lambda: pg.evaluate("TN.vLog[0]&&TN.vLog[0].res")
        spoken_after = lambda n: pg.evaluate("(n)=>TN.spoken.slice(n)", n)

        # ---------- "Trilha" nas outras hipóteses ----------
        vs = await calls('voiceStart')
        check('assistente liga com a sensibilidade normal (sem reforço, sem palavras parecidas)', vs and vs[0].get('high') is False and 'trilho' not in vs[0]['words'], str(vs[:1]))
        await heard('próxima', ['trilha próxima']); await pg.wait_for_timeout(150)
        mk = await calls('mediaKey')
        check('"Trilha" só na 2ª hipótese: o comando vale (antes era ignorado)', mk and mk[-1].get('key') == 'next' and 'comando' in (await last_log()), str(mk) + ' ' + str(await last_log()))
        await heard('a', ['trilha'])
        lg = await last_log(); rest = await pg.evaluate("vArmedT-Date.now()")
        check('"Trilha" sozinho na 2ª hipótese: espera o comando por 8 s', 'esperando o comando' in lg and '2ª hipótese' in lg and 7000 < rest <= 8000, '%s %s' % (lg, rest))
        await pg.evaluate("vArmedT=0")
        n = len(await calls('mediaKey'))
        await heard('trilho próxima')
        check('sensibilidade normal: "trilho" não chama o assistente', len(await calls('mediaKey')) == n and 'sem "Trilha"' in (await last_log()), await last_log())

        # ---------- sensibilidade alta ----------
        await pg.evaluate("openPhone()"); await pg.wait_for_timeout(400)
        check('Telefone mostra o ajuste de sensibilidade (normal) e o atender por voz (ligado)', await pg.evaluate("[document.querySelector('#sVSens').value,document.querySelector('#sVCall').checked]") == ['normal', True])
        await pg.select_option('#sVSens', 'alta'); await pg.wait_for_timeout(200)
        vw, sens = await calls('voiceWords'), await calls('voiceSens')
        check('alta: a gramática ganha "trilho/trilhas" e o nativo liga o reforço do microfone', vw and {'trilho', 'trilhas'} <= set(vw[-1]['words']) and sens and sens[-1] == {'high': True}, '%s %s' % (vw[-1:], sens))
        check('… e fica guardada', json.loads(await pg.evaluate("localStorage.getItem('tn_cfg')"))['vSens'] == 'alta')
        await heard('trilho próxima'); await pg.wait_for_timeout(150)
        check('alta: "trilho próxima" vale', len(await calls('mediaKey')) == n + 1, await last_log())
        await pg.select_option('#sVSens', 'normal'); await pg.wait_for_timeout(200)
        check('voltando ao normal: tira as palavras e o reforço', 'trilho' not in (await calls('voiceWords'))[-1]['words'] and (await calls('voiceSens'))[-1] == {'high': False})

        # ---------- WhatsApp: pessoas escolhidas ----------
        await pg.evaluate("TN.cfg.waRead='nome'")
        sp0 = len(await pg.evaluate("TN.spoken"))
        await pg.evaluate("__emit('whatsapp',{app:'WhatsApp',title:'Ana Paula',text:'Chego às 8',t:Date.now()})"); await pg.wait_for_timeout(200)
        check('antes de escolher: "só quem mandou"', (await spoken_after(sp0)) == ['Mensagem de Ana Paula'], str(await spoken_after(sp0)))
        await pg.evaluate("renderWa()"); await pg.wait_for_timeout(100)
        await pg.evaluate("document.querySelector('#phWa [data-wasel=\"0\"]').click()"); await pg.wait_for_timeout(200)
        check('☆ na mensagem escolhe a pessoa (★, e aparece na lista)', '★' in await pg.text_content('#phWa') and 'Ana Paula' in await pg.text_content('#waSelList'), await pg.text_content('#waSelList'))
        sp0 = len(await pg.evaluate("TN.spoken"))
        await pg.evaluate("__emit('whatsapp',{app:'WhatsApp',title:'Ana Paula',text:'Estou na portaria',t:Date.now()+1})"); await pg.wait_for_timeout(200)
        await pg.evaluate("__emit('whatsapp',{app:'WhatsApp',title:'Beto',text:'Segredo do Beto',t:Date.now()+2})"); await pg.wait_for_timeout(200)
        await pg.evaluate("__emit('whatsapp',{app:'WhatsApp',title:'Ana Paula @ Família',text:'Mensagem no grupo',t:Date.now()+3})"); await pg.wait_for_timeout(200)
        sp = await spoken_after(sp0)
        check('escolhida: lê quem mandou e o texto; outro: só o nome (ajuste "só quem mandou"); grupo com o nome dela: lê o texto',
              sp == ['Mensagem de Ana Paula: Estou na portaria', 'Mensagem de Beto', 'Mensagem de Ana Paula @ Família: Mensagem no grupo'], str(sp))
        await pg.evaluate("TN.cfg.waRead='nada'")
        sp0 = len(await pg.evaluate("TN.spoken"))
        await pg.evaluate("__emit('whatsapp',{app:'WhatsApp',title:'Beto',text:'Outra do Beto',t:Date.now()+4})"); await pg.wait_for_timeout(200)
        await pg.evaluate("__emit('whatsapp',{app:'WhatsApp',title:'Ana Paula',text:'Saindo',t:Date.now()+5})"); await pg.wait_for_timeout(200)
        sp = await spoken_after(sp0)
        check('ajuste "não": os outros ficam em silêncio e a escolhida continua sendo lida', sp == ['Mensagem de Ana Paula: Saindo'], str(sp))
        await pg.evaluate("waSelSet([...waSelGet(),'Ana'])")
        sp0 = len(await pg.evaluate("TN.spoken"))
        await pg.evaluate("__emit('whatsapp',{app:'WhatsApp',title:'Mariana',text:'Texto da Mariana',t:Date.now()+7})"); await pg.wait_for_timeout(200)
        check('"Ana" na lista não lê o texto de "Mariana" (palavra inteira; revisão 2.7.11)', not any('Texto da Mariana' in x for x in await spoken_after(sp0)), str(await spoken_after(sp0)))
        await pg.evaluate("waSelSet(waSelGet().filter(n=>n!=='Ana'))")
        await pg.fill('#waSelIn', 'Ca'); await pg.click('#waSelAdd'); await pg.wait_for_timeout(200)
        check('nome com menos de 3 letras não entra (pegaria todo mundo)', 'Ca' not in json.loads(await pg.evaluate("localStorage.getItem('tn_waSel')")))
        await pg.fill('#waSelIn', 'Carla'); await pg.click('#waSelAdd'); await pg.wait_for_timeout(200)
        sel = json.loads(await pg.evaluate("localStorage.getItem('tn_waSel')"))
        check('escolher pelo nome digitado; a lista fica no aparelho (tn_waSel)', sel == ['Ana Paula', 'Carla'], str(sel))
        await pg.evaluate("document.querySelector('#waSelList [data-wadel=\"0\"]').click()"); await pg.wait_for_timeout(200)
        sel = json.loads(await pg.evaluate("localStorage.getItem('tn_waSel')"))
        check('× tira da lista', sel == ['Carla'], str(sel))
        txt = await pg.evaluate("document.querySelector('#waSelList').innerHTML")
        await pg.evaluate("__emit('whatsapp',{app:'WhatsApp',title:'<img src=x onerror=window.__x=1>',text:'oi',t:Date.now()+6})"); await pg.evaluate("renderWa()")
        await pg.evaluate("document.querySelector('#phWa [data-wasel=\"0\"]').click()"); await pg.wait_for_timeout(200)
        check('nome com HTML não vira código na lista', not await pg.evaluate("window.__x") and '<img' not in await pg.evaluate("document.querySelector('#waSelList').innerHTML"))
        ext = [u for u in reqs if not u.startswith('http://localhost') and 'cdnjs' not in u and 'fonts.g' not in u]
        check('nada do WhatsApp vai para a rede', not [u for u in ext if 'Ana' in u or 'Beto' in u or 'Carla' in u], str(ext[:3]))
        check('sem erros de página', not errs, str(errs[:3]))
        await b.close()
    print('\nRESULTADO:', 'tudo certo' if not FAILS else 'FALHOU ' + str(FAILS))
    sys.exit(1 if FAILS else 0)

asyncio.run(main())
