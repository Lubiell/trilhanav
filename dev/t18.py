"""v2.3: assistente de voz sempre ligado (Vosk no aparelho), agenda completa e diagnóstico do WhatsApp. Nativo simulado:
o que se testa é o app (palavra de ativação "trilha", vocabulário, botão Voz, agenda, diagnóstico). O reconhecimento em si foi
testado à parte com o mesmo modelo Vosk e voz sintética pt-BR (ver CLAUDE.md)."""
import asyncio, sys
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html'
FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

FAKE = """
window.__calls=[];window.__ls={};window.__listenQ=[];localStorage.setItem('tn_updT',String(Date.now()));
window.__status={phone:true,contacts:true,mic:true,notifAccess:true,speech:true,installAllowed:true,sdk:34,voiceOn:true,
  notif:{connected:false,seen:12,seenWa:3,sentWa:0,lastSkip:'resumo do grupo',lastPkgs:['com.whatsapp','com.android.systemui']}};
window.__agenda=[{name:'Maria Souza',number:'+55 31 99999-0000'},{name:'João Antônio',number:'31 3333-1111'},{name:'Mãe',number:'3122223333'},{name:'Oficina do Zé',number:'3144445555'}];
window.__emit=(ev,d)=>(window.__ls[ev]||[]).forEach(f=>f(d));
const rec=m=>async o=>{__calls.push([m,o||{}])};
window.Capacitor={isNativePlatform:()=>true,getPlatform:()=>'android',registerPlugin:(n)=>({
  addWatcher:async()=>'w1',removeWatcher:async()=>{},requestNotifications:async()=>{},speak:rec('speak'),mediaKey:rec('mediaKey'),
  addListener:(ev,cb)=>{(__ls[ev]=__ls[ev]||[]).push(cb);return Promise.resolve({remove(){}})},
  answerCall:rec('answerCall'),endCall:rec('endCall'),placeCall:rec('placeCall'),volume:rec('volume'),spotifyPlay:rec('spotifyPlay'),
  phoneStatus:async()=>__status,requestPhone:async()=>__status,openNotifAccess:rec('openNotifAccess'),openAppSettings:rec('openAppSettings'),
  listContacts:async()=>{__calls.push(['listContacts',{}]);return {list:__agenda}},
  findContacts:async o=>{__calls.push(['findContacts',o]);return {list:[]}},
  voiceStart:async o=>{__calls.push(['voiceStart',o]);setTimeout(()=>__emit('voice',{state:'on'}),50)},
  voiceStop:async()=>{__calls.push(['voiceStop',{}]);__emit('voice',{state:'off'})},
  voiceWords:async o=>{__calls.push(['voiceWords',o])},
  listen:async o=>{__calls.push(['listen',o]);const t=__listenQ.shift();if(!t)throw new Error('não entendi');return {texts:t}},
  appInfo:async()=>({version:'2.3.0',code:20300}),installApk:rec('installApk')})};
"""

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        ctx = await b.new_context(viewport={'width': 1280, 'height': 720})
        await ctx.add_init_script(FAKE)
        await ctx.route('**/lib/capacitor.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=''))
        pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(URL); await pg.wait_for_timeout(2200)
        calls = lambda m: pg.evaluate('(m)=>__calls.filter(c=>c[0]===m).map(c=>c[1])', m)
        spoken = lambda: pg.evaluate('TN.spoken.slice()')
        heard = lambda t: pg.evaluate("(t)=>__emit('heard',{text:t})", t)

        # ---------- liga sozinho, com a agenda no vocabulário ----------
        vs = await calls('voiceStart')
        words = vs[0]['words'] if vs else []
        check('assistente liga sozinho ao abrir (permissão de microfone dada)', len(vs) == 1 and await pg.evaluate('TN.voiceSt') == 'on')
        check('vocabulário: comandos + nomes da agenda (com acento)', all(w in words for w in ['trilha', 'atender', 'próxima', 'maria', 'joão', 'antônio', 'mãe', 'oficina']) and len(words) < 800, str(len(words)))
        check('botão Voz fica verde "Ouvindo"', await pg.evaluate("document.querySelector('#bVoice').classList.contains('live')&&document.querySelector('#bVoice span').textContent==='Ouvindo'"))

        # ---------- palavra de ativação ----------
        for t in ['pausar', 'música tocar', 'para mãe', '[unk] ligar para maria']:
            await heard(t)
        await pg.wait_for_timeout(300)
        check('conversa sem "trilha" não faz nada (nem música, nem ligação)', not await calls('mediaKey') and not await calls('spotifyPlay') and not await calls('placeCall') and not await pg.evaluate("document.querySelector('#callBox').classList.contains('on')"))
        await heard('[unk] trilha próxima música'); await pg.wait_for_timeout(200)
        check('"trilha próxima música" → próxima', (await calls('mediaKey')) == [{'key': 'next'}])
        await heard('trilha'); await pg.wait_for_timeout(100)
        check('"trilha" sozinho: bipe e "Fale o comando…"', 'Fale o comando' in await pg.text_content('#toast'))
        await heard('pausar'); await pg.wait_for_timeout(200)
        check('… e o próximo comando vale sem "trilha"', (await calls('mediaKey'))[-1] == {'key': 'pause'})
        await heard('pausar'); await pg.wait_for_timeout(200)
        check('… só uma vez (depois volta a exigir "trilha")', len(await calls('mediaKey')) == 2)
        await heard('trilha ligar para mãe'); await pg.wait_for_timeout(300)
        check('"trilha ligar para mãe": acha "Mãe" na agenda carregada (sem perguntar ao Android)', await pg.text_content('#callWho') == 'Mãe' and not await calls('findContacts'), await pg.text_content('#callWho'))
        await heard('trilha cancelar'); await pg.wait_for_timeout(200)
        check('"trilha cancelar" nos 3 s cancela', not await pg.evaluate("document.querySelector('#callBox').classList.contains('on')") and (await spoken())[-1] == 'Ligação cancelada')
        await heard('trilha ligar para joão'); await pg.wait_for_timeout(300)
        check('nome com acento na agenda ("João Antônio") é achado por "joão"', await pg.text_content('#callWho') == 'João Antônio')
        await pg.wait_for_timeout(3700)
        check('… e liga depois de 3,5 s', (await calls('placeCall'))[-1] == {'number': '3133331111'})
        await pg.evaluate("__emit('call',{state:'idle'})")
        await pg.evaluate("__listenQ.push(['Oficina do Zé'])")
        await heard('trilha ligar para'); await pg.wait_for_timeout(1900)
        check('"ligar para" sem nome (fora do vocabulário): pergunta "Para quem?" e ouve pelo Google', 'Para quem?' in await spoken() and len(await calls('listen')) == 1 and await pg.text_content('#callWho') == 'Oficina do Zé')
        await heard('trilha cancelar'); await pg.wait_for_timeout(200)

        # ---------- ligação tocando ----------
        await pg.evaluate("__emit('call',{state:'ringing',number:'+5531999990000',name:'Maria Souza'})"); await pg.wait_for_timeout(4500)
        check('com o assistente ligado, ao tocar não abre a escuta do Google (o microfone é do assistente)', len(await calls('listen')) == 1)
        await heard('música'); await pg.wait_for_timeout(150)
        check('tocando: palavra solta que não é atender/recusar é ignorada', not await calls('spotifyPlay'))
        await heard('atender'); await pg.wait_for_timeout(150)
        check('tocando: "atender" sozinho atende', len(await calls('answerCall')) == 1)
        await pg.evaluate("__emit('call',{state:'idle'})")

        # ---------- botão Voz com o assistente ligado ----------
        await pg.click('#bVoice'); await pg.wait_for_timeout(100)
        await heard('aumentar volume'); await pg.wait_for_timeout(200)
        check('botão Voz arma o assistente (não abre o Google) e o comando vale sem "trilha"', (await calls('volume')) == [{'dir': 'up'}] and len(await calls('listen')) == 1)

        # ---------- estados ----------
        await pg.evaluate("__emit('voice',{state:'paused'})")
        check('em pausa (app falando / ligação): botão mostra "Voz (pausa)"', await pg.text_content('#bVoice span') == 'Voz (pausa)')
        await pg.evaluate("__emit('voice',{state:'error',msg:'microfone ocupado'})")
        check('erro do assistente aparece na tela', 'microfone ocupado' in await pg.text_content('#toast'))
        await pg.evaluate("__emit('voice',{state:'on'})")

        # ---------- tela do telefone: agenda, diagnóstico, liga/desliga ----------
        await pg.click('#bPhone'); await pg.wait_for_timeout(500)
        r = await pg.evaluate("({n:document.querySelectorAll('#phRes [data-rcall]').length,c:document.querySelector('#phCount').textContent,d:document.querySelector('#phDiag').textContent,v:document.querySelector('#sVoiceAlways').checked})")
        check('Telefone mostra a agenda inteira sem precisar digitar', r['n'] == 4 and r['c'].startswith('4 contatos'), str(r))
        check('diagnóstico do WhatsApp: serviço não conectado, contagens e motivo', 'NÃO conectado' in r['d'] and 'do WhatsApp: 3' in r['d'] and 'resumo do grupo' in r['d'], r['d'])
        await pg.fill('#phQ', 'joao'); await pg.wait_for_timeout(400)
        check('filtro sem acento: "joao" acha "João Antônio"', await pg.evaluate("document.querySelectorAll('#phRes [data-rcall]').length") == 1 and 'João Antônio' in await pg.text_content('#phRes'))
        await pg.evaluate("__agenda.push({name:'Pedro Novo',number:'31988887777'})")
        await pg.fill('#phQ', ''); await pg.click('#phRefresh'); await pg.wait_for_timeout(400)
        check('"Atualizar contatos" relê a agenda e atualiza o vocabulário', await pg.evaluate("document.querySelectorAll('#phRes [data-rcall]').length") == 5 and 'pedro' in (await calls('voiceWords'))[-1]['words'])
        await pg.click('#sVoiceAlways'); await pg.wait_for_timeout(200)
        check('desligar "sempre ligado" para o assistente', len(await calls('voiceStop')) == 1 and await pg.evaluate('TN.voiceSt') == 'off' and not await pg.evaluate('TN.cfg.voiceAlways'))
        await pg.click('#sVoiceAlways'); await pg.wait_for_timeout(300)
        check('… e ligar de novo', len(await calls('voiceStart')) == 2 and await pg.evaluate('TN.voiceSt') == 'on')
        await pg.evaluate("document.querySelector('#dlgPhone').close()")

        # ---------- sem permissão de microfone: não liga, avisa ao ligar à mão ----------
        await pg.evaluate("__status.mic=false;TN.cfg.voiceAlways=false")
        await pg.click('#bPhone'); await pg.wait_for_timeout(300); await pg.click('#sVoiceAlways'); await pg.wait_for_timeout(300)
        check('sem microfone: avisa para permitir', 'Permita o microfone' in await pg.text_content('#toast') and len(await calls('voiceStart')) == 2)
        check('sem erros de página', not errs, str(errs[:3]))
        await b.close()
    print('\nRESULTADO:', 'tudo certo' if not FAILS else 'FALHAS: ' + '; '.join(FAILS))
    sys.exit(1 if FAILS else 0)

asyncio.run(main())
