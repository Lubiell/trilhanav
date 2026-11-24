"""v2.7.4–2.7.5: comandos de voz só para música, uma palavra forte por ação (2.7.5), bipes de entendi/não entendi e diagnóstico
(últimas frases ouvidas). Antes: comandos de voz só para música (o dono mandou tirar o resto: "ir para <cidade>", ligações, onde estou, radares por voz…).
O vocabulário do assistente sempre ligado (VBASE, gramática do Vosk) cobre toda palavra que o intérprete (parseCmd) entende e nada
além disso; as frases de música viram o comando certo; as dos comandos que saíram não fazem nada; hipóteses alternativas do Vosk;
o "cancelar/estou bem" do aviso de queda continua. Nativo simulado."""
import asyncio, re, sys, unicodedata
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html'
FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

# ---------- 1) vocabulário x intérprete (sem navegador) ----------
html = open('../index.html', encoding='utf-8').read()
na = lambda t: unicodedata.normalize('NFD', t).encode('ascii', 'ignore').decode()
vb = re.search(r"const VBASE='([^']*)'", html).group(1).split()
vbn = {na(w) for w in vb}
i = html.index('function parseCmd(t)'); j = html.index('  return null}\n', i)
words = set()
for lit in re.findall(r'/(\^?(?:\\.|[^/\n])+)/\.(?:test|exec)', html[i:j]):
    body = re.sub(r'\\[a-zA-Z]', ' ', lit)
    words |= {w for w in re.findall(r'[a-zà-ú]+', body) if len(w) > 1}
words -= {'test', 'exec'}
falta = sorted(w for w in words if na(w) not in vbn)
check('toda palavra que o intérprete entende está no vocabulário do assistente (senão o Vosk nunca a escreve)', not falta, str(falta))
check('vocabulário sem repetição e sem palavras que soam como outra ação (troca/toca, passa/pausa, volta/toca, para/pausa)', len(vb) == len(set(vb)) and not ({'troca', 'trocar', 'passa', 'passar', 'volta', 'voltar', 'para', 'pra', 'pare', 'parar'} & set(vb)), str(len(vb)))
sobra = sorted(w for w in vb if len(na(w)) > 2 and na(w) not in words and w not in {'trilha', 'que', 'por', 'favor', 'não', 'quero', 'música', 'volume', 'som'})
check('vocabulário só com os comandos de música e do aviso de queda (sem ir/atender/hospital/blitz…)', not sobra and not ({'ir', 'atender', 'ligação', 'hospital', 'blitz', 'onde', 'clima', 'posto', 'zoom'} & set(vb)), str(sobra))
gone = [x for x in ('placeGrammar', 'vosk-words', 'PALIAS', 'goPlace', 'askPlace', 'callByName', 'radMarkVoice', 'poiGo', 'callVoice', 'Para onde?') if x in html]
check('saiu o "ir para" por voz, as cidades na gramática, ligar por voz e marcar aviso por voz', not gone, str(gone))

MUSICA = [
    ('próxima', 'next'), ('próxima música', 'next'), ('toca a próxima', 'next'), ('anterior', 'prev'), ('música anterior', 'prev'),
    ('pausar', 'pause'), ('pausa a música', 'pause'), ('aumentar volume', 'volup'), ('aumenta o som', 'volup'), ('abaixar volume', 'voldown'), ('abaixa o volume', 'voldown'),
    ('tocar', 'play'), ('toca música', 'play'), ('voltar a tocar', 'play'), ('estou bem', 'none'), ('tô bem', 'none'), ('cancelar', 'none'),
]
SAIU = ['ir para guidoval', 'quero ir para ouro preto', 'me leva no posto', 'ir para o hospital', 'ligar para maria', 'atender', 'recusar',
        'onde estou', 'quanto falta', 'repetir', 'que horas são', 'velocidade', 'clima', 'vai chover', 'posto', 'hospital', 'farmácia',
        'marcar blitz', 'marcar radar', 'apagar aviso', 'travar tela', 'gravar trilha', 'ler mensagens', 'ajuda', 'aproximar', 'autonomia', 'abasteci',
        # sinônimos que saíram na 2.7.5 (uma palavra por ação)
        'trocar música', 'pula essa', 'outra música', 'volta a música', 'desligar a música', 'para a música', 'mais volume', 'baixa o som', 'diminui o volume',
        'liga a música', 'continuar', 'esquece', 'tudo bem']

FAKE = """
window.__calls=[];window.__ls={};window.__listenQ=[];localStorage.setItem('tn_updT',String(Date.now()));
window.__beeps=[];window.AudioContext=function(){this.currentTime=0;this.destination={};
  this.createOscillator=()=>{const o={frequency:{value:0},connect(){},start(){__beeps.push(o.frequency.value)},stop(){}};return o};this.createGain=()=>({gain:{value:0},connect(){}})};
localStorage.setItem('tn_sosC',JSON.stringify([{name:'Ana',number:'31999990000'}]));
window.__status={phone:true,contacts:true,mic:true,notifAccess:true,speech:true,installAllowed:true,sdk:34,voiceOn:true,notif:{connected:true}};
window.__emit=(ev,d)=>(window.__ls[ev]||[]).forEach(f=>f(d));
const rec=m=>async o=>{__calls.push([m,o||{}])};
window.Capacitor={isNativePlatform:()=>true,getPlatform:()=>'android',registerPlugin:(n)=>({
  addWatcher:async()=>'w1',removeWatcher:async()=>{},requestNotifications:async()=>{},speak:rec('speak'),mediaKey:rec('mediaKey'),
  addListener:(ev,cb)=>{(__ls[ev]=__ls[ev]||[]).push(cb);return Promise.resolve({remove(){}})},
  answerCall:rec('answerCall'),endCall:rec('endCall'),placeCall:rec('placeCall'),volume:rec('volume'),spotifyPlay:rec('spotifyPlay'),sendSms:rec('sendSms'),
  phoneStatus:async()=>__status,requestPhone:async()=>__status,
  listContacts:async()=>({list:[{name:'Maria Souza',number:'31999990000'}]}),findContacts:async o=>{__calls.push(['findContacts',o]);return {list:[]}},
  voiceStart:async o=>{__calls.push(['voiceStart',o]);setTimeout(()=>__emit('voice',{state:'on'}),50)},voiceStop:rec('voiceStop'),
  voiceWords:rec('voiceWords'),voiceBt:rec('voiceBt'),
  listen:async o=>{__calls.push(['listen',o]);const t=__listenQ.shift();if(!t)throw new Error('não entendi');return {texts:t}},
  appInfo:async()=>({version:'2.7.4',code:20704})})};
"""

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        ctx = await b.new_context(viewport={'width': 1280, 'height': 720})
        await ctx.add_init_script(FAKE)
        reqs = []
        async def route(r):
            u = r.request.url; reqs.append(u)
            if u.endswith('/lib/capacitor.js'): await r.fulfill(status=200, content_type='application/javascript', body=''); return
            if u.startswith('http://localhost') or 'cdnjs.cloudflare.com' in u or 'fonts.g' in u: await r.continue_(); return
            await r.abort()   # sem internet
        await ctx.route('**/*', route)
        pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(URL); await pg.wait_for_timeout(2200)
        calls = lambda m: pg.evaluate('(m)=>__calls.filter(c=>c[0]===m).map(c=>c[1])', m)
        spoken = lambda: pg.evaluate('TN.spoken.slice()')
        beeps = lambda: pg.evaluate('window.__beeps.slice()')
        vlog = lambda: pg.evaluate('TN.vLog.map(x=>[x.src,x.text,x.res])')
        heard = lambda t, alts=None: pg.evaluate("([t,a])=>TN.onHeard(a?{text:t,alts:a}:{text:t})", [t, alts])
        async def said_after(n0): return (await spoken())[n0:]

        # ---------- 2) frases ----------
        got = await pg.evaluate("ps=>ps.map(t=>{const c=TN.parseCmd(t);return c&&c.a})", [f for f, _ in MUSICA])
        bad = [(f, e, g) for (f, e), g in zip(MUSICA, got) if g != e]
        check('frases de música entendidas como o comando certo (%d)' % len(MUSICA), not bad, str(bad))
        got = await pg.evaluate("ps=>ps.map(t=>{const c=TN.parseCmd(t);return c&&c.a})", SAIU)
        bad = [(f, g) for f, g in zip(SAIU, got) if g is not None]
        check('comandos que saíram não viram nada (%d frases)' % len(SAIU), not bad, str(bad))

        # ---------- 3) assistente sempre ligado ----------
        vs = await calls('voiceStart')
        w = set(vs[0]['words']) if vs else set()
        check('assistente liga com o vocabulário fixo (sem agenda nem cidades)', vs and w == set(vb) and 'maria' not in w, str(len(w)))
        check('o app não procura mais o vocabulário do modelo (lib/vosk-words.txt)', not [u for u in reqs if 'vosk-words' in u])
        b0 = len(await beeps()); await heard('trilha próxima música'); await pg.wait_for_timeout(250)
        check('"trilha próxima música" → próxima', (await calls('mediaKey')) == [{'key': 'next'}])
        check('entendeu: dois bipes agudos', (await beeps())[b0:] == [1500, 1500], str((await beeps())[b0:]))
        check('diagnóstico: frase ouvida e o comando', (await vlog())[0] == ['v', 'trilha próxima música', 'comando: próxima música'], str((await vlog())[:1]))
        b0 = len(await beeps()); await heard('próxima música'); await pg.wait_for_timeout(250)
        check('conversa sem "trilha" não faz nada (nem bipe)', len(await calls('mediaKey')) == 1 and (await beeps())[b0:] == [])
        check('diagnóstico: conversa sem "trilha" aparece como ignorada', (await vlog())[0] == ['v', 'próxima música', 'ignorado: sem "Trilha"'], str((await vlog())[:1]))
        await heard('[unk] trilha [unk] pausar'); await pg.wait_for_timeout(100)
        check('diagnóstico mostra o que o modelo não conhece como "…"', (await vlog())[0] == ['v', '… trilha … pausar', 'comando: pausar'], str((await vlog())[:1]))
        await heard('trilha'); await heard('aumentar o volume')
        check('"trilha" sozinho arma e o comando seguinte vale', (await calls('volume')) == [{'dir': 'up'}])
        await heard('trilha de a o', ['trilha de a o', 'trilha pausar'])
        check('a 2ª hipótese vale quando a 1ª não é comando', (await calls('mediaKey'))[-1] == {'key': 'pause'} and (await vlog())[0][2] == 'comando: pausar (pela 2ª hipótese)', str((await vlog())[:1]))
        n0 = len(await spoken()); await heard('trilha ir para guidoval'); await pg.wait_for_timeout(1600)
        s = await said_after(n0)
        check('"trilha, ir para Guidoval": não procura nem pergunta "Para onde?"', s == ['Não entendi: ir para guidoval'] and not await calls('listen') and not await pg.evaluate('!!TN.nav'), str(s))
        n0 = len(await spoken()); await heard('trilha ligar para maria'); await pg.wait_for_timeout(300)
        check('"trilha, ligar para Maria": não liga', (await said_after(n0)) == ['Não entendi: ligar para maria'] and not await calls('findContacts') and not await calls('placeCall'))
        n0 = len(await spoken()); b0 = len(await beeps()); await heard('trilha mapa')
        check('não entendeu: um bipe grave e diz o que ouviu', (await said_after(n0)) == ['Não entendi: mapa'] and (await beeps())[b0:] == [330], str((await beeps())[b0:]))
        check('diagnóstico: "não entendi"', (await vlog())[0] == ['v', 'trilha mapa', 'não entendi'], str((await vlog())[:1]))
        n0 = len(await spoken()); await heard('trilha de a o')
        check('só palavras soltas ("de a o"): diz apenas "Não entendi"', (await said_after(n0)) == ['Não entendi'])

        # ---------- 4) ligação: só os botões da tela ----------
        n0 = len(await spoken())
        await pg.evaluate("__emit('call',{state:'ringing',number:'+5531999990000',name:'Maria Souza'})"); await pg.wait_for_timeout(4500)
        r = await pg.evaluate("({st:document.querySelector('#callSt').textContent,ans:getComputedStyle(document.querySelector('#callAns')).display})")
        check('ligação chegando: anuncia quem liga, sem pedir "atender ou recusar" e sem escutar', (await said_after(n0)) == ['Ligação de Maria Souza'] and r['st'] == 'Ligação chegando' and r['ans'] != 'none' and not await calls('listen'), str(r))
        await heard('atender'); await heard('trilha atender')
        check('"atender" por voz não atende mais', not await calls('answerCall'))
        await pg.click('#callAns'); await pg.wait_for_timeout(100)
        check('botão Atender da tela atende', len(await calls('answerCall')) == 1)
        await pg.evaluate("__emit('call',{state:'idle'})")
        set_html = await pg.evaluate("document.querySelector('#dlgPhone').innerHTML")
        check('Telefone sem a opção "Ligação: escutar atender ou recusar"; ajuda da voz só com música', 'sCallVoice' not in set_html and 'próxima música' in set_html and 'ir para' not in set_html.lower(), '')

        # ---------- 5) aviso de queda: "cancelar" vale sem "trilha"; música sem "trilha" não ----------
        await pg.evaluate("document.querySelector('#sosTestB').click()"); await pg.wait_for_timeout(300)
        check('teste do aviso de queda contando', await pg.evaluate("TN.sos&&TN.sos.phase") == 'count')
        k0 = len(await calls('mediaKey')); await heard('próxima música')
        check('no aviso, frase de música sem "trilha" não faz nada', len(await calls('mediaKey')) == k0 and await pg.evaluate("TN.sos&&TN.sos.phase") == 'count')
        await heard('cancelar'); await pg.wait_for_timeout(200)
        check('no aviso, "cancelar" sem "trilha" cancela (nada enviado)', await pg.evaluate("TN.sos") is None and not await calls('sendSms') and (await spoken())[-1] == 'Aviso cancelado')

        # ---------- 6) botão Voz (escuta do Google) com o assistente desligado ----------
        await pg.evaluate("TN.cfg.voiceAlways=false;TN.onVoiceState({state:'off'})")
        await pg.evaluate("__listenQ.push(['ir para Ouro Preto'],['próxima'])")
        n0 = len(await spoken()); await pg.click('#bVoice'); await pg.wait_for_timeout(400)
        check('botão Voz: "ir para Ouro Preto" não faz nada', (await said_after(n0)) == ['Não entendi: ir para Ouro Preto'] and not await pg.evaluate('!!TN.nav'), str(await said_after(n0)))
        k0 = len(await calls('mediaKey')); b0 = len(await beeps()); await pg.click('#bVoice'); await pg.wait_for_timeout(400)
        check('botão Voz: "próxima" passa, com os dois bipes (depois do bipe de "fale agora")', (await calls('mediaKey'))[k0:] == [{'key': 'next'}] and (await beeps())[b0:] == [1000, 1500, 1500], str((await beeps())[b0:]))
        check('diagnóstico: frase do botão Voz', (await vlog())[0] == ['g', 'próxima', 'comando: próxima música'] and (await vlog())[1] == ['g', 'ir para Ouro Preto', 'não entendi'], str((await vlog())[:2]))

        # ---------- 7) tela: diagnóstico, dica do intercomunicador; nada guardado ----------
        for k in range(12): await heard('conversa %d' % k)
        await pg.click('#bPhone'); await pg.wait_for_timeout(400)
        r = await pg.evaluate("({n:document.querySelectorAll('#vLog .lr').length,first:document.querySelector('#vLog .lr')&&document.querySelector('#vLog .lr').textContent,html:document.querySelector('#dlgPhone').innerHTML})")
        check('Telefone mostra as últimas 10 frases ouvidas (a mais nova em cima)', r['n'] == 10 and r['first'] and '"conversa 11"' in r['first'] and 'ignorado' in r['first'], str(r['n']) + ' ' + str(r['first'])[:80])
        check('Telefone tem a dica dos botões do intercomunicador e a explicação dos bipes', 'intercomunicador' in r['html'] and 'bipe grave' in r['html'] and 'Diagnóstico da voz' in r['html'])
        await heard('trilha pausar'); await pg.wait_for_timeout(150)
        check('com a tela aberta, a lista atualiza sozinha', 'comando: pausar' in await pg.evaluate("document.querySelector('#vLog .lr').textContent"))
        await heard('<img src=x onerror="window.__xss=1"> trilha'); await pg.wait_for_timeout(150)
        check('texto ouvido entra sem HTML', not await pg.evaluate('!!window.__xss') and not await pg.evaluate("!!document.querySelector('#vLog img')"))
        ls = await pg.evaluate("Object.keys(localStorage).map(k=>localStorage.getItem(k)).join(' ')")
        check('frases ouvidas não ficam guardadas no aparelho', 'conversa' not in ls and 'mapa' not in ls)
        check('sem erros', not errs, str(errs))
        await b.close()
    print('\nRESULTADO:', 'tudo certo' if not FAILS else 'FALHOU ' + str(FAILS))
    sys.exit(1 if FAILS else 0)

asyncio.run(main())
