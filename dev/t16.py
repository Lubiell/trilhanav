"""v2.2: telefone (atender/recusar/ligar pela tela), WhatsApp, música atual, comandos de voz (só música desde a v2.7.4) e atualização do APK.
O lado nativo (Capacitor + TrilhaNativePlugin) é simulado: o que se testa é o app. Ligação, WhatsApp e microfone de verdade
só no celular (não há emulador Android neste ambiente)."""
import asyncio, json, sys
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html'
FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

FAKE = """
window.__calls=[];if(!sessionStorage.__x){sessionStorage.__x=1;localStorage.setItem('tn_updT',String(Date.now()))}window.__ls={};window.__listenQ=[];window.__contacts=[];window.__status={phone:true,contacts:true,mic:true,notifAccess:false,speech:true,installAllowed:true,sdk:34};
window.__emit=(ev,d)=>(window.__ls[ev]||[]).forEach(f=>f(d));
const rec=(n,m)=>async o=>{__calls.push([m,o||{}]);};
window.Capacitor={isNativePlatform:()=>true,getPlatform:()=>'android',registerPlugin:(n)=>({
  addWatcher:async(o,cb)=>'w1',removeWatcher:async()=>{},requestNotifications:async()=>{},
  speak:rec(n,'speak'),mediaKey:rec(n,'mediaKey'),openApp:rec(n,'openApp'),openUrl:rec(n,'openUrl'),
  addListener:(ev,cb)=>{(__ls[ev]=__ls[ev]||[]).push(cb);return Promise.resolve({remove(){}})},
  answerCall:rec(n,'answerCall'),endCall:rec(n,'endCall'),placeCall:rec(n,'placeCall'),volume:rec(n,'volume'),spotifyPlay:rec(n,'spotifyPlay'),
  requestPhone:async()=>{__calls.push(['requestPhone',{}]);return __status},openNotifAccess:rec(n,'openNotifAccess'),openAppSettings:rec(n,'openAppSettings'),
  phoneStatus:async()=>__status,
  findContacts:async o=>{__calls.push(['findContacts',o]);return {list:__contacts}},
  listen:async o=>{__calls.push(['listen',o]);const t=__listenQ.shift();if(!t)throw new Error('não entendi');return {texts:t}},
  appInfo:async()=>({version:'2.2.0',code:20200}),
  installApk:async o=>{__calls.push(['installApk',o])}})};
"""

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        ctx = await b.new_context(viewport={'width': 1280, 'height': 720})
        await ctx.add_init_script(FAKE)
        ver = {'v': {'version': '2.3.0', 'code': 20300, 'apk': 'https://raw.githubusercontent.com/Lubiell/trilhanav/apk/trilhanav-2.3.0.apk', 'sha256': 'ab' * 32, 'notes': 'Correções <b>x</b>'}}
        async def vjson(route):
            await route.fulfill(status=200, headers={'Access-Control-Allow-Origin': '*'}, content_type='application/json', body=json.dumps(ver['v']))
        await ctx.route('https://raw.githubusercontent.com/Lubiell/trilhanav/apk/versao.json**', vjson)
        # no pacote do APK (www/) o capacitor.js de verdade carregaria por cima do simulado
        await ctx.route('**/lib/capacitor.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=''))
        pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(URL); await pg.wait_for_timeout(1200)
        calls = lambda m: pg.evaluate('(m)=>__calls.filter(c=>c[0]===m).map(c=>c[1])', m)
        spoken = lambda: pg.evaluate('TN.spoken.slice()')
        await pg.evaluate("TN.cfg.updAuto=false")

        # ---------- botões ----------
        r = await pg.evaluate("['bPhone','bVoice'].map(id=>!!document.querySelector('#'+id+' svg.ic use'))")
        check('botões Telefone e Voz na barra, com ícone', r == [True, True])

        # ---------- intérprete de comandos: só música (v2.7.4) ----------
        casos = {'pausar': 'pause', 'próxima música': 'next', 'música anterior': 'prev', 'aumentar o volume': 'volup', 'abaixa o volume': 'voldown',
                 'tocar Spotify': 'play', 'toca música': 'play', 'cancelar': 'none', 'bom dia': None,
                 'Atender': 'answer', 'recusar': 'end', 'ligar para Maria': 'callto', 'Liga pro João da Silva': 'callto', 'ler mensagens': None}   # ligar para favorito voltou na 2.7.12 (t33)
        res = await pg.evaluate("(cs)=>Object.fromEntries(cs.map(t=>{const c=TN.parseCmd(t);return [t,c?c.a:null]}))", list(casos))
        bad = {k: (res[k], v) for k, v in casos.items() if res[k] != v}
        check('frases de música viram o comando certo; atender/recusar (2.7.11) e ligar para (2.7.12) voltaram; ler por voz continua fora', not bad, str(bad))

        # ---------- ligação chegando: botões da tela (a escuta de "atender/recusar" saiu na v2.7.4) ----------
        await pg.evaluate("__emit('call',{state:'ringing',number:'+5531999990000',name:'Maria Souza'})")
        await pg.wait_for_timeout(300)
        r = await pg.evaluate("({on:document.querySelector('#callBox').classList.contains('on'),who:document.querySelector('#callWho').textContent,ans:getComputedStyle(document.querySelector('#callAns')).display,st:document.querySelector('#callSt').textContent})")
        check('ligação chegando: tela com o nome e os botões Atender/Recusar', r['on'] and r['who'] == 'Maria Souza' and r['ans'] != 'none' and r['st'] == 'Ligação chegando', str(r))
        check('voz anuncia quem liga', (await spoken())[-1] == 'Ligação de Maria Souza')
        await pg.wait_for_timeout(4600)
        check('o app não abre a escuta sozinho', not await calls('listen') and not await calls('answerCall'))
        await pg.click('#callAns'); await pg.wait_for_timeout(100)
        check('botão Atender atende', len(await calls('answerCall')) == 1)
        await pg.evaluate("__emit('call',{state:'offhook',number:'',name:''})"); await pg.wait_for_timeout(100)
        r = await pg.evaluate("({on:document.querySelector('#callBox').classList.contains('on'),b:document.querySelector('#callEnd').textContent,who:document.querySelector('#callWho').textContent})")
        check('em ligação: botão Desligar e nome mantido', r == {'on': True, 'b': 'Desligar', 'who': 'Maria Souza'}, str(r))
        await pg.evaluate("__emit('call',{state:'idle',number:'',name:''})"); await pg.wait_for_timeout(100)
        check('ligação terminou: tela some', not await pg.evaluate("document.querySelector('#callBox').classList.contains('on')"))

        # ---------- recusar pelo botão; número desconhecido ----------
        await pg.evaluate("__emit('call',{state:'ringing',number:'',name:''})"); await pg.wait_for_timeout(300)
        check('número desconhecido é anunciado', (await spoken())[-1] == 'Ligação de número desconhecido')
        await pg.click('#callEnd'); await pg.wait_for_timeout(100)
        check('botão Recusar chama endCall', len(await calls('endCall')) == 1)
        await pg.evaluate("__emit('call',{state:'idle'})")
        await pg.evaluate("document.querySelector('#dlgSet').showModal()")
        await pg.evaluate("__emit('call',{state:'ringing',number:'123',name:'X'})"); await pg.wait_for_timeout(100)
        check('ligação chegando fecha o diálogo aberto (senão bloqueia os botões)', not await pg.evaluate("document.querySelector('#dlgSet').open"))
        await pg.click('#callAns', timeout=3000); await pg.wait_for_timeout(100)
        check('botão Atender funciona com o diálogo que estava aberto', len(await calls('answerCall')) == 2)
        await pg.evaluate("__emit('call',{state:'idle'})")

        # ---------- tela do telefone: escolher e favoritar ----------
        await pg.evaluate("TN.openPhone([{name:'João Silva',number:'1'},{name:'João Pedro',number:'2'}])"); await pg.wait_for_timeout(300)
        r = await pg.evaluate("({open:document.querySelector('#dlgPhone').open,n:document.querySelectorAll('#phRes [data-rcall]').length})")
        check('tela do telefone lista os contatos com Ligar', r == {'open': True, 'n': 2}, str(r))
        await pg.click('#phRes [data-fav="1"]'); await pg.wait_for_timeout(100)
        check('☆ adiciona aos favoritos', 'João Pedro' in await pg.text_content('#phFavs'))
        await pg.click('#phFavs [data-call="0"]'); await pg.wait_for_timeout(3800)
        check('Ligar do favorito liga depois de 3,5 s (só dígitos)', (await calls('placeCall'))[-1:] == [{'number': '2'}], str(await calls('placeCall')))
        await pg.evaluate("__emit('call',{state:'idle'})")

        # ---------- música ----------
        for frase, metodo, arg in [('próxima música', 'mediaKey', {'key': 'next'}), ('pausar', 'mediaKey', {'key': 'pause'}), ('aumentar o volume', 'volume', {'dir': 'up'}), ('tocar música', 'spotifyPlay', {})]:
            await pg.evaluate("(f)=>__listenQ.push([f])", frase)
            await pg.click('#bVoice'); await pg.wait_for_timeout(400)
            c = await calls(metodo)
            check(f'voz "{frase}" → {metodo}', c and c[-1] == arg, str(c[-1:] if c else c))
        await pg.evaluate("__emit('media',{active:true,pkg:'com.spotify.music',title:'Música <b>Boa</b>',artist:'Banda',playing:true})")
        check('música atual aparece (Spotify), sem HTML', await pg.text_content('#mNow') == '▶ Música <b>Boa</b> — Banda (Spotify)' and 'Música' in await pg.text_content('#toast'))
        await pg.evaluate("__listenQ.push(['tocar'])"); await pg.click('#bVoice'); await pg.wait_for_timeout(400)
        check('com player ativo, "tocar" manda play para ele', (await calls('mediaKey'))[-1] == {'key': 'play'})
        await pg.evaluate("document.querySelector('#bSpot').click()"); await pg.wait_for_timeout(200); await pg.click('#mSpotBg'); await pg.wait_for_timeout(200)
        check('botão "Tocar no Spotify (sem sair daqui)"', len(await calls('spotifyPlay')) == 2)
        await pg.evaluate("document.querySelector('#dlgMedia').close()")

        # ---------- WhatsApp ----------
        n0 = len(await spoken())
        msg = {'app': 'WhatsApp', 'title': 'João', 'text': 'Chego em 5 <img src=x onerror="window.__xss=1">', 't': 1000}
        await pg.evaluate("(m)=>__emit('whatsapp',m)", msg); await pg.wait_for_timeout(150)
        r = await pg.evaluate("({on:document.querySelector('#waCard').classList.contains('on'),t:document.querySelector('#waT').textContent,x:document.querySelector('#waX').textContent,img:!!document.querySelector('#waCard img'),xss:!!window.__xss})")
        check('mensagem do WhatsApp vira cartão (texto puro, sem HTML)', r['on'] and r['t'] == 'João' and r['x'] == msg['text'] and not r['img'] and not r['xss'], str(r))
        check('voz diz só quem mandou (padrão)', (await spoken())[n0:] == ['Mensagem de João'])
        await pg.evaluate("(m)=>__emit('whatsapp',m)", msg); await pg.wait_for_timeout(100)
        check('mensagem repetida não é anunciada de novo', (await spoken())[n0:] == ['Mensagem de João'] and await pg.evaluate('TN.waMsgs.length') == 1)
        await pg.evaluate("TN.cfg.waRead='tudo';__emit('whatsapp',{app:'WhatsApp',title:'Ana',text:'Oi',t:2000})"); await pg.wait_for_timeout(100)
        check('"quem mandou e o texto" lê a mensagem', (await spoken())[-1] == 'Mensagem de Ana: Oi')
        await pg.evaluate("__emit('call',{state:'ringing',name:'Z',number:'9'})"); await pg.wait_for_timeout(100); m0 = len(await spoken())
        await pg.evaluate("__emit('whatsapp',{app:'WhatsApp',title:'Bia',text:'durante a ligação',t:3000})"); await pg.wait_for_timeout(100)
        check('durante a ligação a mensagem não é lida em voz alta', len(await spoken()) == m0)
        await pg.evaluate("__emit('call',{state:'idle'})")
        ls = await pg.evaluate("Object.keys(localStorage).map(k=>localStorage.getItem(k)).join(' ')")
        check('texto das mensagens não fica guardado no aparelho', 'Chego em 5' not in ls and 'durante a ligação' not in ls)

        # ---------- tela do telefone e permissões ----------
        await pg.click('#bPhone'); await pg.wait_for_timeout(300)
        r = await pg.evaluate("({perm:document.querySelector('#phPerm').textContent,notif:getComputedStyle(document.querySelector('#phNotif')).display,req:getComputedStyle(document.querySelector('#phReq')).display,hint:document.querySelector('#phHint').textContent,wa:document.querySelectorAll('#phWa .lr').length})")
        check('Telefone mostra o que falta liberar e a dica do Android 13+', 'falta' in r['perm'] and r['notif'] != 'none' and r['req'] == 'none' and 'configurações restritas' in r['hint'] and r['wa'] == 3, str(r))
        await pg.click('#phNotif'); await pg.wait_for_timeout(100)
        check('"Liberar acesso a notificações" abre a tela do Android', len(await calls('openNotifAccess')) == 1)
        await pg.fill('#phNum', '(31) 3333-4444'); await pg.click('#phDial'); await pg.wait_for_timeout(3800)
        check('discar número digitado', (await calls('placeCall'))[-1] == {'number': '3133334444'})
        await pg.evaluate("__emit('call',{state:'idle'})")

        # ---------- atualização ----------
        await pg.evaluate("document.querySelector('#bSet').click()"); await pg.wait_for_timeout(200)
        check('Ajustes mostram a versão instalada', 'Versão instalada: 2.2.0' in await pg.text_content('#updInfo'))
        await pg.click('#bUpd'); await pg.wait_for_timeout(500)
        r = await pg.evaluate("({open:document.querySelector('#dlgAsk').open,t:document.querySelector('#askT').textContent,m:document.querySelector('#askMsg').textContent,html:document.querySelector('#askMsg').innerHTML})")
        check('versão nova: pergunta antes, com as notas (sem HTML)', r['open'] and '2.3.0' in r['t'] and 'Correções <b>x</b>' in r['m'] and '<b>' not in r['html'], str(r)[:200])
        await pg.click('#askOk'); await pg.wait_for_timeout(300)
        ia = await calls('installApk')
        check('"Atualizar agora" baixa o APK do branch apk com o SHA-256', ia == [{'url': ver['v']['apk'], 'sha256': 'ab' * 32}], str(ia))
        ver['v'] = dict(ver['v'], code=20200)
        await pg.click('#bUpd'); await pg.wait_for_timeout(500)
        check('mesma versão: "já tem a mais nova", sem perguntar', not await pg.evaluate("document.querySelector('#dlgAsk').open") and 'mais nova' in await pg.text_content('#toast'))
        ver['v'] = dict(ver['v'], code=20400, sha256='xyz')
        await pg.click('#bUpd'); await pg.wait_for_timeout(500)
        check('versao.json inválido: não instala', len(await calls('installApk')) == 1 and 'inválido' in await pg.text_content('#toast'))
        await pg.evaluate("document.querySelector('#dlgSet').close()")

        # ---------- o controle de guidão saiu (v2.7.2): uma tecla gravada antes não chama mais a voz ----------
        await pg.evaluate("localStorage.setItem('tn_keys',JSON.stringify({voice:'KeyV'}))")
        await pg.reload(); await pg.wait_for_timeout(1200)
        n0 = len(await calls('listen'))
        await pg.keyboard.press('KeyV'); await pg.wait_for_timeout(300)
        check('tecla gravada no tempo do controle de guidão não faz nada e o tn_keys sai', len(await calls('listen')) == n0 and await pg.evaluate("localStorage.getItem('tn_keys')") is None)
        await pg.screenshot(path='/tmp/claude-0/-home-user/51ac65f6-457e-5d09-b14e-b860846fbcdb/scratchpad/png/t16.png')

        # ---------- celular: tela da ligação em retrato ----------
        await pg.set_viewport_size({'width': 360, 'height': 780})
        await pg.evaluate("__emit('call',{state:'ringing',number:'+5531999990000',name:'Fulano de Tal com Nome Comprido'})"); await pg.wait_for_timeout(300)
        r = await pg.evaluate("(()=>{const b=document.querySelector('#callBox').getBoundingClientRect();return {l:b.left,r:b.right,w:innerWidth}})()")
        check('tela da ligação cabe em 360 px', r['l'] >= 0 and r['r'] <= r['w'], str(r))
        await pg.screenshot(path='/tmp/claude-0/-home-user/51ac65f6-457e-5d09-b14e-b860846fbcdb/scratchpad/png/t16_call.png')
        check('sem erros de página', not errs, str(errs[:3]))
        await b.close()

        # ---------- no navegador (sem APK): só avisa ----------
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome'); pg = await b.new_page(); errs2 = []
        pg.on('pageerror', lambda e: errs2.append(str(e)))
        await pg.goto(URL); await pg.wait_for_timeout(1000)
        await pg.click('#bPhone'); t1 = await pg.text_content('#toast'); await pg.click('#bVoice'); t2 = await pg.text_content('#toast')
        check('no navegador: Telefone e Voz avisam que é só no app', 'só funciona no app' in t1 and 'só funcionam no app' in t2 and not errs2, f'{t1} | {t2} {errs2}')
        await b.close()
    print('\nRESULTADO:', 'tudo certo' if not FAILS else 'FALHAS: ' + '; '.join(FAILS))
    sys.exit(1 if FAILS else 0)

asyncio.run(main())
