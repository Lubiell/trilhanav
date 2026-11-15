"""Etapa 7: integração do app com o APK (Capacitor). Aqui o Capacitor é simulado: o que se testa é o lado do app
(GPS em segundo plano, voz nativa, controle de mídia, Spotify). O lado nativo (Java) só é compilado/testado no APK."""
import asyncio, sys
from playwright.async_api import async_playwright

FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

FAKE_CAP = """
window.__calls=[];window.__bgcb=null;window.__bgfail=false;
window.Capacitor={isNativePlatform:()=>true,getPlatform:()=>'android',registerPlugin:(n)=>({
  addWatcher:async(o,cb)=>{__calls.push([n,'addWatcher',o]);window.__bgcb=cb;return 'w1'},
  removeWatcher:async o=>{__calls.push([n,'removeWatcher',o])},
  requestNotifications:async()=>{__calls.push([n,'requestNotifications'])},
  speak:async o=>{__calls.push([n,'speak',o])},
  mediaKey:async o=>{if(window.__mediaFail)throw new Error('x');__calls.push([n,'mediaKey',o])},
  openApp:async o=>{__calls.push([n,'openApp',o])}})};
"""

async def newpage(b, native=True):
    ctx = await b.new_context(viewport={'width': 1600, 'height': 720})
    if native: await ctx.add_init_script(FAKE_CAP)
    pg = await ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
    await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(1300)
    return pg, errs

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')

        # ================= dentro do APK =================
        pg, errs = await newpage(b)
        check('detecta o app nativo', await pg.evaluate('TN.NATIVE'))
        calls = await pg.evaluate('__calls')
        names = [c[1] for c in calls]
        check('pede a permissão de notificação e abre o serviço de GPS em segundo plano', names[:2] == ['requestNotifications', 'addWatcher'], str(names))
        opt = next(c[2] for c in calls if c[1] == 'addWatcher')
        check('o serviço tem título/mensagem de notificação (necessário para seguir com a tela apagada)', opt.get('backgroundMessage') and opt.get('backgroundTitle') == 'TrilhaNav' and opt.get('requestPermissions') is True and opt.get('stale') is False, str(opt))
        # posições vindas do serviço nativo entram como GPS normal
        r = await pg.evaluate('''()=>{const t=Date.now();for(let i=0;i<6;i++)__bgcb({latitude:-20,longitude:-44+i*0.0003,altitude:900,accuracy:6,speed:12,bearing:90,time:t+i*2000,simulated:false},undefined);
          return {total:TN.st.total,gps:document.querySelector('#gpsTxt').textContent,spd:document.querySelector('#speed').textContent,hdg:document.querySelector('#hdgTxt').textContent}}''')
        check('posições do serviço nativo alimentam odômetro, velocidade e rumo', r['total'] > 0.1 and r['gps'] == 'GPS ±6 m' and r['spd'] == '43' and '090' in r['hdg'], str(r))
        r = await pg.evaluate('''()=>{__bgcb({latitude:-20,longitude:-43.99,altitude:null,accuracy:5,speed:null,bearing:null,time:Date.now()+99999},undefined);return document.querySelector('#gpsTxt').textContent}''')
        check('posição sem velocidade/rumo/altitude (null) não quebra', r == 'GPS ±5 m', r)
        r = await pg.evaluate('''()=>{__bgcb(undefined,{code:'NOT_AUTHORIZED'});return [document.querySelector('#gpsTxt').textContent,document.querySelector('#toast').textContent]}''')
        check('sem permissão de localização: avisa o que fazer', r[0] == 'GPS sem permissão' and 'o tempo todo' in r[1], str(r))
        # voz nativa
        await pg.evaluate('()=>{TN.cfg.voice=true;TN.cfg.voiceVol=0.7;TN.say("Em 200 metros, curva à direita",true)}')
        sp = await pg.evaluate("__calls.filter(c=>c[1]==='speak')")
        check('a voz do copiloto vai para o TTS nativo (volume e urgência)', len(sp) == 1 and sp[0][2] == {'text': 'Em 200 metros, curva à direita', 'volume': 0.7, 'urgent': True}, str(sp))
        await pg.evaluate('()=>{TN.cfg.voice=false;TN.say("mudo")}')
        check('voz desligada não chama o TTS', len(await pg.evaluate("__calls.filter(c=>c[1]==='speak')")) == 1)
        # música
        await pg.click('#bSpot'); await pg.wait_for_timeout(200)
        check('no APK o botão 🎵 abre o painel de música', await pg.evaluate("document.querySelector('#dlgMedia').open"))
        await pg.click('#mNext'); await pg.click('#mPlay'); await pg.click('#mPrev')
        keys = await pg.evaluate("__calls.filter(c=>c[1]==='mediaKey').map(c=>c[2].key)")
        check('próxima / tocar-pausar / anterior mandam a tecla de mídia', keys == ['next', 'playpause', 'previous'], str(keys))
        await pg.click('#mOpen'); await pg.wait_for_timeout(100)
        check('"Abrir o Spotify" chama o app pelo pacote', await pg.evaluate("__calls.filter(c=>c[1]==='openApp').map(c=>c[2].package)") == ['com.spotify.music'])
        await pg.click('#dlgMedia [data-close]')
        # teclas configuráveis do controle de guidão
        await pg.click('#bSet')
        acts = await pg.evaluate("[...document.querySelectorAll('#keyList [data-a]')].map(b=>b.dataset.a)")
        check('ações de música aparecem entre as teclas configuráveis', all(a in acts for a in ('mediaPlay', 'mediaNext', 'mediaPrev')), str(acts))
        await pg.click('[data-a=mediaNext]'); await pg.keyboard.press('KeyN'); await pg.click('#dlgSet [data-close]')
        await pg.keyboard.press('KeyN'); await pg.wait_for_timeout(100)
        keys = await pg.evaluate("__calls.filter(c=>c[1]==='mediaKey').map(c=>c[2].key)")
        check('tecla do controle mapeada para "próxima" manda a tecla de mídia', keys[-1] == 'next' and len(keys) == 4, str(keys))
        await pg.evaluate('()=>{window.__mediaFail=true}'); await pg.click('#bSpot'); await pg.click('#mPlay'); await pg.wait_for_timeout(200)
        check('falha do nativo no controle de mídia avisa em vez de quebrar', 'Não consegui controlar a música' in await pg.text_content('#toast'))
        await pg.evaluate('()=>{window.__mediaFail=false}')
        # simulação de GPS substitui o serviço
        await pg.evaluate('()=>{TN.cfg.sim=true}')
        check('sem erros (APK)', not errs, str(errs))
        await pg.context.close()

        # ================= no navegador comum =================
        pg, errs = await newpage(b, native=False)
        check('no navegador não é nativo', not await pg.evaluate('TN.NATIVE'))
        await pg.evaluate('()=>{TN.say("oi")}')
        check('no navegador a voz continua usando speechSynthesis (sem chamar o nativo)', await pg.evaluate("typeof window.__calls==='undefined'"))
        # controle de mídia pelo teclado no navegador: só avisa
        await pg.evaluate("document.querySelector('#bSet').click()")
        await pg.click('[data-a=mediaPlay]'); await pg.keyboard.press('KeyM'); await pg.evaluate("document.querySelector('#dlgSet').close()")
        await pg.keyboard.press('KeyM'); await pg.wait_for_timeout(100)
        check('no navegador, tecla de música só explica que precisa do APK', 'só funciona no app' in await pg.text_content('#toast'))
        check('sem erros (navegador)', not errs, str(errs))
        await b.close()
    print('\nRESULTADO:', 'FALHOU ' + str(FAILS) if FAILS else 'tudo certo')
    sys.exit(1 if FAILS else 0)
asyncio.run(main())
