"""v2.7.2: comandos de voz. O vocabulário do assistente sempre ligado (VBASE, gramática do Vosk) cobre toda palavra que o
intérprete (parseCmd) entende; jeitos novos de falar; comandos novos (onde estou, quanto falta, repetir, velocidade, hora,
aproximar/afastar, travar tela, gravar, ajuda); hipóteses alternativas do Vosk. Usa dev/testmap.pmtiles (fixtures.py)."""
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
i = html.index('const POIK=') if 'const POIK=' in html else html.index('const GORE=/'); j = html.index('  return null}\n', html.index('function parseCmd(t)'))
words = set()
for lit in re.findall(r'/(\^?(?:\\.|[^/\n])+)/\.(?:test|exec)|=/(\^?(?:\\.|[^/\n])+)/;|\[/((?:\\.|[^/\n])+)/,', html[i:j]):
    body = re.sub(r'\\[a-zA-Z]', ' ', lit[0] or lit[1] or lit[2])
    words |= {w for w in re.findall(r'[a-zà-ú]+', body) if len(w) > 1}
words -= {'test', 'exec'}
falta = sorted(w for w in words if na(w) not in vbn)
check('toda palavra que o intérprete entende está no vocabulário do assistente (senão o Vosk nunca a escreve)', not falta, str(falta))
check('vocabulário sem repetição e com "trocar" (antes faltava: "trocar música" virava "tocar")', len(vb) == len(set(vb)) and 'trocar' in vb, str(len(vb)))

PHRASES = [
    ('trocar música', 'next'), ('troca a música', 'next'), ('outra música', 'next'), ('pula essa', 'next'), ('próxima', 'next'),
    ('música anterior', 'prev'), ('pausar', 'pause'), ('para a música', 'pause'),
    ('mais volume', 'volup'), ('aumenta o som', 'volup'), ('sobe o volume', 'volup'),
    ('menos volume', 'voldown'), ('baixa o som', 'voldown'), ('diminui o volume', 'voldown'),
    ('liga a música', 'play'), ('tocar spotify', 'play'), ('toca rádio', 'play'),
    ('atende', 'answer'), ('não atender', 'end'), ('recusar', 'end'), ('desliga', 'end'),
    ('ligar para maria', 'call'), ('quero ir para ouro preto', 'go'), ('me leva pra casa', 'go'), ('ir para', 'go'),
    ('cancelar rota', 'stopnav'), ('desligar navegação', 'stopnav'),
    ('onde estou', 'where'), ('onde eu tô', 'where'), ('minha localização', 'where'),
    ('quanto falta', 'eta'), ('quanto tempo falta', 'eta'), ('hora de chegada', 'eta'), ('qual a distância', 'eta'),
    ('repetir', 'repeat'), ('repete', 'repeat'), ('fala de novo', 'repeat'),
    ('velocidade', 'speed'), ('qual o limite', 'speed'), ('que horas são', 'time'),
    ('ajuda', 'help'), ('o que eu posso falar', 'help'),
    ('aproximar', 'zin'), ('mais zoom', 'zin'), ('aumenta o zoom', 'zin'), ('afastar', 'zout'), ('menos zoom', 'zout'),
    ('travar tela', 'lock'), ('destravar', 'lock'), ('gravar trilha', 'rec'), ('parar gravação', 'rec'),
    ('clima', 'wx'), ('vai chover', 'wx'), ('quanto tempo vai chover', 'wx'), ('onde está o posto', 'fuel'), ('não quero', None), ('posto', 'fuel'), ('autonomia', 'range'), ('abasteci', 'filled'), ('marcar radar', 'radar'),
    ('ler mensagens', 'read'), ('estou bem', 'none'), ('esquece', 'none'),
]
STUB = "window.__spk=[];Object.defineProperty(window,'speechSynthesis',{value:{speak:u=>window.__spk.push(u.text),cancel(){},getVoices(){return []}},configurable:true});localStorage.setItem('tn_updT',String(Date.now()));"
ONPOS = '''([lat,lon,t,v])=>TN.onPos({timestamp:t,coords:{latitude:lat,longitude:lon,altitude:0,accuracy:5,speed:v||0,heading:null}})'''
VA, PA = (-20.0, -44.303), (-20.003, -43.703)

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        ctx = await b.new_context(viewport={'width': 1280, 'height': 720})
        await ctx.add_init_script(STUB)
        async def route(r):
            u = r.request.url
            if u.startswith('http://localhost') or 'cdnjs.cloudflare.com' in u or 'fonts.g' in u: await r.continue_(); return
            await r.abort()   # sem internet
        await ctx.route('**/*', route)
        pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(URL); await pg.wait_for_timeout(1300)
        spk = lambda: pg.evaluate('window.__spk.slice()')
        async def last_said(n0):
            s = await spk(); return s[n0:]

        # ---------- 2) jeitos de falar ----------
        got = await pg.evaluate("ps=>ps.map(t=>{const c=TN.parseCmd(t);return c&&c.a})", [p_ for p_, _ in PHRASES])
        bad = [(f, e, g) for (f, e), g in zip(PHRASES, got) if g != e]
        check('frases entendidas como o comando certo (%d)' % len(PHRASES), not bad, str(bad))
        r = await pg.evaluate("[TN.parseCmd('travar tela').on,TN.parseCmd('destravar a tela').on,TN.parseCmd('gravar trilha').on,TN.parseCmd('parar gravação').on,TN.parseCmd('quero ir para ouro preto').where,TN.parseCmd('ir para').where]")
        check('travar/destravar, gravar/parar e o destino saem certos', r == [True, False, True, False, 'ouro preto', ''], str(r))

        # ---------- 3) comandos novos ----------
        await pg.set_input_files('#offIn', 'testmap.pmtiles'); await pg.wait_for_timeout(2500)
        t = 1_000_000_000_000
        await pg.evaluate(ONPOS, [VA[0], VA[1], t, 0]); await pg.evaluate(ONPOS, [VA[0], VA[1], t + 1000, 10])
        n0 = len(await spk()); await pg.evaluate("TN.runCmd({a:'speed'})")
        check('"velocidade" fala a velocidade', any('36 quilômetros por hora' in x for x in await last_said(n0)), str(await last_said(n0)))
        n0 = len(await spk()); await pg.evaluate("TN.runCmd({a:'time'})")
        s = await last_said(n0)
        check('"que horas são" fala a hora', s and re.match(r'^(São \d+ horas|É uma hora|É meia-noite)', s[-1]), str(s))
        n0 = len(await spk()); await pg.evaluate("TN.runCmd({a:'where'})"); await pg.wait_for_timeout(800)
        s = await last_said(n0)
        check('"onde estou" diz a rua e a cidade pelo mapa offline', s and s[-1].startswith('Você está na Rua') and s[-1].endswith('em Vila Alegre'), str(s))
        z0 = await pg.evaluate('TN.map.getZoom()')
        await pg.evaluate("TN.runCmd({a:'zin'})"); await pg.wait_for_timeout(400); z1 = await pg.evaluate('TN.map.getZoom()')
        await pg.evaluate("TN.runCmd({a:'zout'})"); await pg.wait_for_timeout(400); z2 = await pg.evaluate('TN.map.getZoom()')
        check('"aproximar"/"afastar" mudam o zoom do mapa', z1 == z0 + 1 and z2 == z0, str((z0, z1, z2)))
        await pg.evaluate("TN.runCmd({a:'lock',on:true})"); l1 = await pg.text_content('#lockIco')
        await pg.evaluate("TN.runCmd({a:'lock',on:true})"); l2 = await pg.text_content('#lockIco')
        await pg.evaluate("TN.runCmd({a:'lock',on:false})"); l3 = await pg.text_content('#lockIco')
        check('"travar tela" trava (repetir não destrava) e "destravar" libera', (l1, l2, l3) == ('🔒', '🔒', '🔓'), str((l1, l2, l3)))
        await pg.evaluate("TN.runCmd({a:'rec',on:true})"); r1 = await pg.evaluate("document.querySelector('#bRec').classList.contains('rec')")
        await pg.evaluate("TN.runCmd({a:'rec',on:false})"); r2 = await pg.evaluate("document.querySelector('#bRec').classList.contains('rec')")
        check('"gravar trilha" grava e "parar gravação" pausa', r1 and not r2, str((r1, r2)))
        n0 = len(await spk()); await pg.evaluate("TN.runCmd({a:'help'})")
        s = await last_said(n0)
        check('"ajuda" lista os comandos', s and 'quanto falta' in s[-1] and 'próxima música' in s[-1], str(s)[:120])
        n0 = len(await spk()); await pg.evaluate("TN.runCmd({a:'eta'})")
        check('"quanto falta" sem rota avisa', (await last_said(n0)) == ['Nenhuma rota'], str(await last_said(n0)))

        # com rota (62 km sem internet até Pedra Azul)
        await pg.evaluate("(async()=>{const rt=await TN.offNavReq({lat:%f,lon:%f},{lat:%f,lon:%f});TN.navStart(rt,{lat:%f,lon:%f,name:'Pedra Azul'})})()" % (VA + PA + PA))
        await pg.wait_for_timeout(500)
        await pg.evaluate(ONPOS, [VA[0], VA[1], t + 3000, 10]); await pg.evaluate(ONPOS, [VA[0], VA[1] + 0.0003, t + 6000, 10])
        n0 = len(await spk()); await pg.evaluate("TN.runCmd({a:'eta'})")
        s = await last_said(n0)
        check('"quanto falta" com rota: distância, tempo e hora de chegada', s and re.match(r'^Faltam (6\d|5\d)(,\d)? quilômetros, cerca de .+\. Chegada às \d+ e \d\d$', s[-1]), str(s))
        n0 = len(await spk()); await pg.evaluate("TN.runCmd({a:'repeat'})")
        s = await last_said(n0)
        check('"repetir" repete a próxima manobra com a distância de agora', s and s[-1].startswith('Em '), str(s))
        await pg.evaluate("TN.navStop()")
        n0 = len(await spk()); await pg.evaluate("TN.runCmd({a:'repeat'})")
        s = await last_said(n0)
        check('"repetir" fora da rota repete a última fala', s and s[-1] and not s[-1].startswith('Nada'), str(s))

        # ---------- 4) o que o assistente sempre ligado ouviu (Vosk), com hipóteses ----------
        n0 = len(await spk()); await pg.evaluate("TN.onHeard({text:'trilha ir para [unk] [unk]'})"); await pg.wait_for_timeout(300)
        s = await last_said(n0)
        check('"trilha, ir para <lugar fora do vocabulário>" pergunta "Para onde?"', s and s[0] == 'Para onde?', str(s))
        await pg.wait_for_timeout(1500)
        n0 = len(await spk()); await pg.evaluate("TN.onHeard({text:'trilha que horas são',alts:['trilha que horas são']})")
        s = await last_said(n0)
        check('"trilha que horas são" responde', s and re.match(r'^(São|É uma|É meia-noite)', s[-1]), str(s))
        n0 = len(await spk()); await pg.evaluate("TN.onHeard({text:'trilha de a o',alts:['trilha de a o','trilha que horas são']})")
        s = await last_said(n0)
        check('a 2ª hipótese vale quando a 1ª não é comando', s and re.match(r'^(São|É uma|É meia-noite)', s[-1]), str(s))
        n0 = len(await spk()); await pg.evaluate("TN.onHeard({text:'de a o',alts:['de a o','trilha que horas são']})")
        check('sem "trilha" na hipótese principal (conversa) nada acontece', not await last_said(n0), str(await last_said(n0)))
        n0 = len(await spk()); await pg.evaluate("TN.onHeard({text:'trilha mapa'})")
        s = await last_said(n0)
        check('não entendeu: diz o que ouviu', s and s[-1] == 'Não entendi: mapa', str(s))
        n0 = len(await spk()); await pg.evaluate("TN.onHeard({text:'trilha de a o'})")
        s = await last_said(n0)
        check('só palavras soltas ("de a o"): diz apenas "Não entendi"', s and s[-1] == 'Não entendi', str(s))
        n0 = len(await spk()); await pg.evaluate("TN.onHeard({text:'trilha'})"); await pg.evaluate("TN.onHeard({text:'velocidade'})")
        s = await last_said(n0)
        check('"trilha" sozinho arma e o comando seguinte vale (frase cortada em duas)', s and 'quilômetros por hora' in s[-1], str(s))
        check('sem erros', not errs, str(errs))
        await b.close()
    print('\nRESULTADO:', 'tudo certo' if not FAILS else 'FALHOU ' + str(FAILS))
    sys.exit(1 if FAILS else 0)

asyncio.run(main())
