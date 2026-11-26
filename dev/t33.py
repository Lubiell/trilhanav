"""v2.7.12 (spec docs/specs/2026-11-25-voz-abas-ir-para-ligar.md, aprovada pelo dono): voz para abas, "ir para" (e "de … para …"),
"ligar para" um favorito, "mandar localização" por SMS, posto, onde estou, quanto falta, nome do assistente e aviso do capacete.
O nome do lugar/pessoa vem da escuta do Google (listen, simulada aqui). Nativo, busca e rota simulados."""
import asyncio, json, sys
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html'
FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

FAKE = """
window.__calls=[];window.__ls={};window.__listenQ=[];window.__smsOk=true;localStorage.setItem('tn_updT',String(Date.now()));
localStorage.setItem('tn_phFav',JSON.stringify([{name:'Emiliane Souza',number:'(31) 98888-7777'},{name:'Carlos',number:'3133334444'}]));
window.__status={phone:true,contacts:true,mic:true,notifAccess:true,speech:true,installAllowed:true,sdk:34,voiceOn:true,notif:{connected:true}};
window.__emit=(ev,d)=>(window.__ls[ev]||[]).forEach(f=>f(d));
const rec=m=>async o=>{__calls.push([m,o||{}])};
window.Capacitor={isNativePlatform:()=>true,getPlatform:()=>'android',registerPlugin:(n)=>({
  addWatcher:async()=>'w1',removeWatcher:async()=>{},requestNotifications:async()=>{},speak:rec('speak'),mediaKey:rec('mediaKey'),
  addListener:(ev,cb)=>{(__ls[ev]=__ls[ev]||[]).push(cb);return Promise.resolve({remove(){}})},
  answerCall:rec('answerCall'),endCall:rec('endCall'),placeCall:rec('placeCall'),volume:rec('volume'),spotifyPlay:rec('spotifyPlay'),sendSms:rec('sendSms'),
  requestSms:async()=>({granted:__smsOk}),navNotify:rec('navNotify'),
  phoneStatus:async()=>__status,requestPhone:async()=>__status,listContacts:async()=>({list:[]}),
  voiceStart:async o=>{__calls.push(['voiceStart',o]);setTimeout(()=>__emit('voice',{state:'on',msg:'fone'}),50)},voiceStop:rec('voiceStop'),
  voiceWords:rec('voiceWords'),voiceBt:rec('voiceBt'),voiceSens:rec('voiceSens'),
  listen:async o=>{__calls.push(['listen',o]);const t=__listenQ.shift();if(!t)throw new Error('não entendi');if(t==='NET')throw new Error('erro de voz 2');return {texts:t}},
  appInfo:async()=>({version:'2.7.12',code:20712})})};
"""
# busca e rota simuladas (a busca de verdade é a mesma da tela, testada no t23/t24)
STUB = """()=>{window.__geo={'guidoval':[{name:'Rua Guidoval',sub:'Ubá',lat:-21.11,lon:-42.94},{name:'Guidoval',sub:'MG (longe)',lat:-15.0,lon:-40.0},{name:'Guidoval',sub:'MG',lat:-21.15,lon:-42.79}],
   'uba':[{name:'Ubá',sub:'MG',lat:-21.12,lon:-42.94}],'ouro preto':[{name:'Ouro Preto',sub:'MG',lat:-20.38,lon:-43.50}]};
  window.geoSearch=async q=>{__calls.push(['geoSearch',{q}]);return (__geo[normTxt(q)]||[]).map(x=>Object.assign({},x))};
  window.anyRoute=async(f,t)=>{__calls.push(['anyRoute',{from:[+f.lat,+f.lon],to:t.name}]);return [offNavRoute(mkRoute([{lat:+f.lat,lon:+f.lon},{lat:+t.lat,lon:+t.lon}]),true)]};
  window.fuelFind=async()=>[{name:'Posto Ipiranga',sub:'',lat:-21.125,lon:-42.945}]}"""
FIX = '''([la,lo,v,h,t])=>TN.onPos({timestamp:t,coords:{latitude:la,longitude:lo,altitude:800,accuracy:5,speed:v,heading:h}})'''

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
        await pg.evaluate(STUB)
        calls = lambda m: pg.evaluate("(m)=>__calls.filter(c=>c[0]===m).map(c=>c[1])", m)
        heard = lambda t: pg.evaluate("(t)=>TN.onHeard({text:t})", t)
        spoken = lambda: pg.evaluate("TN.spoken.slice()")
        async def said_after(n0): return (await spoken())[n0:]
        listenQ = lambda *t: pg.evaluate("(t)=>__listenQ.push(...t)", list(t))
        nav = lambda: pg.evaluate("TN.nav&&{to:TN.nav.to.name,from:TN.nav.from}")

        # ---------- intérprete ----------
        F = [('ir para', 'goto', ''), ('ir pra Ouro Preto', 'goto', 'Ouro Preto'), ('ir de Ubá para Guidoval', 'goto', 'de Ubá para Guidoval'),
             ('ligar para', 'callto', ''), ('ligar para Emiliane', 'callto', 'Emiliane'), ('ligar Carlos', 'callto', 'Carlos'),
             ('mandar localização', 'sendloc', ''), ('mandar a localização para Emiliane', 'sendloc', 'Emiliane'),
             ('onde estou', 'where', None), ('onde eu estou', 'where', None), ('quanto falta', 'eta', None), ('quanto que falta', 'eta', None),
             ('posto', 'fuel', None), ('mapa', 'tab', None), ('painel', 'tab', None), ('telefone', 'tab', None),
             ('desligar a música', None, None), ('liga a música', None, None), ('desligar', 'end', None)]
        got = await pg.evaluate("fs=>fs.map(t=>{const c=parseCmd(t);return c?[c.a,c.q===undefined?null:c.q]:[null,null]})", [f for f, _, _ in F])
        bad = [(f, a, q, g) for (f, a, q), g in zip(F, got) if g[0] != a or (q is not None and g[1] != q)]
        check('frases novas viram o comando certo (e o nome dito pelo botão Voz vem junto)', not bad, str(bad))
        vw = (await calls('voiceStart'))[0]['words']
        check('gramática do Vosk com as palavras novas', {'ir', 'para', 'ligar', 'mapa', 'painel', 'telefone', 'posto', 'onde', 'quanto', 'falta', 'mandar', 'localização'} <= set(vw), str(len(vw)))

        # ---------- abas ----------
        await heard('trilha painel'); await pg.wait_for_timeout(150)
        check('"Trilha, painel" abre o Painel', await pg.evaluate("curPane") == 'paneDash')
        await heard('trilha telefone'); await pg.wait_for_timeout(300)
        check('"Trilha, telefone" abre o Telefone', await pg.evaluate("document.querySelector('#dlgPhone').open"))
        mic = await pg.evaluate("document.querySelector('#vLog').textContent")
        check('Diagnóstico da voz mostra qual microfone está ouvindo (capacete)', 'do capacete' in mic, mic[:80])
        await heard('trilha mapa'); await pg.wait_for_timeout(150)
        check('"Trilha, mapa" fecha o Telefone e volta ao Mapa', await pg.evaluate("curPane") == 'paneMap' and not await pg.evaluate("document.querySelector('#dlgPhone').open"))

        # ---------- ir para ----------
        n0 = len(await spoken()); await heard('trilha ir para'); await pg.wait_for_timeout(300)
        check('sem GPS: pergunta e diz que não tem GPS (não calcula)', 'Para onde?' in await said_after(n0) and not await nav(), str(await said_after(n0)))
        await pg.evaluate(FIX, [-21.12, -42.94, 0, 0, 1_700_000_000_000]); await pg.wait_for_timeout(200)
        await listenQ(['Guidoval', 'Guido Val'])
        n0 = len(await spoken()); await heard('trilha ir para'); await pg.wait_for_timeout(600)
        ls = await calls('listen')
        check('"Trilha, ir para": pergunta "Para onde?" e a escuta do Google espera a pergunta terminar (afterTts)', (await said_after(n0))[:1] == ['Para onde?'] and ls[-1].get('afterTts') is True, str(ls[-1:]))
        nv = await nav(); rt = (await calls('anyRoute'))[-1]
        check('… "Guidoval": entre os resultados com o nome exato, o mais perto; calcula a rota e começa', nv and nv['to'] == 'Guidoval' and abs(await pg.evaluate("TN.nav.to.lat") + 21.15) < 1e-6 and rt['from'] == [-21.12, -42.94], str(nv) + str(rt))
        check('… e fala a rota', any(x.startswith('Rota para Guidoval') for x in await said_after(n0)), str(await said_after(n0)))
        await pg.evaluate("navStop()")
        await listenQ(['de Ubá para Guidoval'])
        await heard('trilha ir para'); await pg.wait_for_timeout(600)
        nv = await nav(); sel = await pg.evaluate("[navSel.from&&navSel.from.name,navSel.to&&navSel.to.name]"); rt = (await calls('anyRoute'))[-1]
        check('"de Ubá para Guidoval": preenche o De e o Para e a rota sai de Ubá', nv and nv['to'] == 'Guidoval' and nv['from'] == 'Ubá' and sel == ['Ubá', 'Guidoval'] and rt['from'] == [-21.12, -42.94], str(nv) + str(sel))
        await pg.evaluate("navStop()")
        await listenQ(['Lugar Nenhum'])
        n0 = len(await spoken()); await heard('trilha ir para'); await pg.wait_for_timeout(500)
        check('lugar que a busca não acha: fala que não achou e não começa rota', 'Não achei Lugar Nenhum' in await said_after(n0) and not await nav(), str(await said_after(n0)))
        await listenQ('NET')
        n0 = len(await spoken()); await heard('trilha ir para'); await pg.wait_for_timeout(400)
        check('escuta do Google sem internet: avisa para usar a tela', 'Não consegui ouvir o lugar sem internet; use a tela' in await said_after(n0), str(await said_after(n0)))
        await pg.evaluate("TN.cfg.voiceAlways=false;TN.onVoiceState({state:'off'})")
        await listenQ(['ir para Ouro Preto'])
        await pg.click('#bVoice'); await pg.wait_for_timeout(600)
        nv = await nav()
        check('botão Voz: "ir para Ouro Preto" de uma vez (sem perguntar de novo)', nv and nv['to'] == 'Ouro Preto' and len(await calls('listen')) == len(ls) + 4, str(nv))
        await pg.evaluate("TN.cfg.voiceAlways=true;TN.onVoiceState({state:'on',msg:'fone'})")

        # ---------- quanto falta / onde estou / posto ----------
        n0 = len(await spoken()); await heard('trilha quanto falta'); await pg.wait_for_timeout(200)
        check('"quanto falta" com rota: distância e hora de chegada', any(x.startswith('Faltam') and 'Chegada às' in x for x in await said_after(n0)), str(await said_after(n0)))
        await pg.evaluate("navStop()")
        n0 = len(await spoken()); await heard('trilha quanto falta'); await pg.wait_for_timeout(200)
        check('"quanto falta" sem rota', (await said_after(n0)) == ['Nenhuma rota'], str(await said_after(n0)))
        n0 = len(await spoken()); await heard('trilha onde estou'); await pg.wait_for_timeout(200)
        check('"onde estou" sem mapa offline: diz que precisa do mapa', any('Sem o mapa offline' in x for x in await said_after(n0)), str(await said_after(n0)))
        await pg.evaluate("offPM={};offH={maxZoom:14};window.nearNames=async()=>[['Rua das Flores',-21.1201,-42.9401,'Rua'],['Ubá',-21.121,-42.941,'Cidade']]")
        n0 = len(await spoken()); await heard('trilha onde estou'); await pg.wait_for_timeout(300)
        check('"onde estou" com mapa offline: rua e cidade', (await said_after(n0)) == ['Você está na Rua das Flores, em Ubá'], str(await said_after(n0)))
        await pg.evaluate("offPM=null;offH=null")
        await pg.evaluate("localStorage.setItem('tn_netOk','true')")
        n0 = len(await spoken()); await heard('trilha posto'); await pg.wait_for_timeout(500)
        sp = await said_after(n0); nv = await nav()
        check('"posto": fala o posto mais perto e calcula a rota até ele', sp and sp[0].startswith('Posto mais perto: Posto Ipiranga, a ') and nv and nv['to'] == 'Posto Ipiranga', str(sp) + str(nv))
        await pg.evaluate("navStop()")

        # ---------- ligar para um favorito ----------
        await listenQ(['Emiliane', 'Emiliano'])
        n0 = len(await spoken()); await heard('trilha ligar para'); await pg.wait_for_timeout(500)
        check('"ligar para" → "Para quem?" → "Emiliane": liga para o favorito pelo primeiro nome, falando o nome antes', (await said_after(n0))[:2] == ['Para quem?', 'Ligando para Emiliane Souza'] and not await calls('placeCall'), str(await said_after(n0)))
        await pg.wait_for_timeout(3600)
        check('… 3,5 s depois liga', (await calls('placeCall')) == [{'number': '31988887777'}], str(await calls('placeCall')))
        await pg.evaluate("__emit('call',{state:'idle'})"); await pg.wait_for_timeout(100)
        await listenQ(['Emiliane'])
        await heard('trilha ligar para'); await pg.wait_for_timeout(500)
        k0 = len(await calls('mediaKey')); await heard('próxima'); await heard('cancelar'); await pg.wait_for_timeout(3600)
        check('"cancelar" sem "Trilha" nos 3,5 s cancela a ligação (e música sem "Trilha" não vale)', len(await calls('placeCall')) == 1 and len(await calls('mediaKey')) == k0 and 'Ligação cancelada' in await spoken())
        await listenQ(['Joaquim'])
        n0 = len(await spoken()); await heard('trilha ligar para'); await pg.wait_for_timeout(4000)
        check('nome fora dos favoritos não liga', len(await calls('placeCall')) == 1 and 'Joaquim não está nos favoritos' in await said_after(n0), str(await said_after(n0)))
        await pg.evaluate("localStorage.setItem('tn_phFav',JSON.stringify([{name:'Emiliane Souza',number:'31988887777'},{name:'Emiliane Casa',number:'3132221111'}]))")
        await listenQ(['Emiliane'])
        n0 = len(await spoken()); await heard('trilha ligar para'); await pg.wait_for_timeout(4000)
        check('dois favoritos com o mesmo nome: fala os dois e não liga', len(await calls('placeCall')) == 1 and any(x.startswith('Tenho Emiliane Souza e Emiliane Casa') for x in await said_after(n0)), str(await said_after(n0)))
        await listenQ(['Emiliane Casa'])
        await heard('trilha ligar para'); await pg.wait_for_timeout(4200)
        check('… com o nome inteiro liga para o certo', (await calls('placeCall'))[-1] == {'number': '3132221111'}, str(await calls('placeCall')))
        await pg.evaluate("__emit('call',{state:'idle'})"); await pg.wait_for_timeout(100)

        # ---------- mandar localização ----------
        await listenQ(['Emiliane Souza'])
        n0 = len(await spoken()); await heard('trilha mandar localização'); await pg.wait_for_timeout(600)
        dl = await pg.evaluate("[document.querySelector('#dlgAsk').open,document.querySelector('#askT').textContent]")
        check('"mandar localização": avisa por voz e na tela, com 5 s para cancelar', 'Mandando sua localização para Emiliane Souza. Diga cancelar' in await said_after(n0) and dl == [True, 'Mandar localização'] and not await calls('sendSms'), str(dl))
        await pg.wait_for_timeout(5000)
        sms = await calls('sendSms')
        check('… 5 s depois manda o SMS só para o favorito, com o link do mapa', len(sms) == 1 and sms[0]['numbers'] == ['31988887777'] and 'https://maps.google.com/?q=-21.120000,-42.940000' in sms[0]['text'] and not await pg.evaluate("document.querySelector('#dlgAsk').open"), str(sms))
        await listenQ(['Emiliane Souza'])
        await heard('trilha mandar localização'); await pg.wait_for_timeout(600)
        await heard('cancelar'); await pg.wait_for_timeout(5200)
        check('"cancelar" sem "Trilha" não manda', len(await calls('sendSms')) == 1 and 'Envio cancelado' in await spoken() and not await pg.evaluate("document.querySelector('#dlgAsk').open"))
        await listenQ(['Emiliane Souza'])
        await heard('trilha mandar localização'); await pg.wait_for_timeout(600)
        await pg.click('#askOk'); await pg.wait_for_timeout(5200)
        check('tocar em "Cancelar o envio" não manda', len(await calls('sendSms')) == 1)
        await pg.evaluate("window.__smsOk=false"); await listenQ(['Emiliane Souza'])
        n0 = len(await spoken()); await heard('trilha mandar localização'); await pg.wait_for_timeout(5600)
        check('sem permissão de SMS não manda', len(await calls('sendSms')) == 1 and 'Sem permissão de SMS' in await said_after(n0), str(await said_after(n0)))

        # ---------- nome do assistente ----------
        await pg.evaluate("openPhone()"); await pg.wait_for_timeout(300)
        await pg.select_option('#sVName', 'piloto'); await pg.wait_for_timeout(200)
        w = (await calls('voiceWords'))[-1]['words']
        check('escolher "Piloto": a gramática troca "trilha" por "piloto"', 'piloto' in w and 'trilha' not in w and json.loads(await pg.evaluate("localStorage.getItem('tn_cfg')"))['vName'] == 'piloto')
        await pg.evaluate("document.querySelector('#dlgPhone').close()")
        k0 = len(await calls('mediaKey')); await heard('piloto próxima'); await heard('trilha próxima'); await pg.wait_for_timeout(200)
        lg = await pg.evaluate("TN.vLog[0].res")
        check('"Piloto, próxima" vale e "Trilha, próxima" não', (await calls('mediaKey'))[k0:] == [{'key': 'next'}] and lg == 'ignorado: sem "Piloto"', lg)
        await pg.evaluate("TN.cfg.vSens='alta'")
        check('com outro nome, "trilho/trilhas" da sensibilidade alta não entram', 'trilho' not in await pg.evaluate("voiceVocab()"))
        await pg.evaluate("TN.cfg.vSens='normal'")
        await pg.evaluate("openPhone()"); await pg.wait_for_timeout(200)
        await pg.select_option('#sVName', 'trilha'); await pg.wait_for_timeout(200)
        check('voltar para "Trilha"', 'trilha' in (await calls('voiceWords'))[-1]['words'])

        # ---------- capacete ----------
        await pg.evaluate("TN.cfg.voiceBt=true")
        n0 = len(await spoken())
        await pg.evaluate("TN.onVoiceState({state:'on',msg:'celular'})"); await pg.wait_for_timeout(200)
        t = await pg.evaluate("document.querySelector('#toast')&&document.querySelector('#toast').textContent")
        check('capacete desconectou no meio do uso: avisa na tela e por voz', 'O microfone do capacete desconectou' in await said_after(n0) and t and 'microfone do capacete não está ligado' in t, str(t))
        mic = await pg.evaluate("document.querySelector('#vLog').textContent")
        check('… e o Diagnóstico mostra o microfone do celular', 'do celular' in mic, mic[:80])
        n0 = len(await spoken()); await pg.evaluate("TN.onVoiceState({state:'on',msg:'celular'})"); await pg.wait_for_timeout(100)
        check('… sem repetir o aviso enquanto continua sem o capacete', not await said_after(n0))

        ext = [u for u in reqs if not u.startswith('http://localhost') and 'cdnjs' not in u and 'fonts.g' not in u]
        check('nenhuma chamada de rede nova (nome, favorito e localização não vão para a internet pelo app)', not [u for u in ext if 'Emiliane' in u or 'maps.google' in u or 'Guidoval' in u], str(ext[:4]))
        check('sem erros de página', not errs, str(errs[:3]))
        await b.close()
    print('\nRESULTADO:', 'tudo certo' if not FAILS else 'FALHOU ' + str(FAILS))
    sys.exit(1 if FAILS else 0)

asyncio.run(main())
