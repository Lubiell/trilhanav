"""Etapa 5: gerenciador de GPX com pastas, notas/fotos na gravação e tema dia/noite automático."""
import asyncio, sys, os, zipfile, tempfile, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from PIL import Image
from playwright.async_api import async_playwright

FAILS = []
def check(nome, ok, extra=''):
    print(('OK   ' if ok else 'FALHA'), nome, extra)
    if not ok: FAILS.append(nome)

TMP = tempfile.mkdtemp(prefix='tn9_')
def utc(h, m=0, d=15): return int(datetime(2026, 11, d, h, m, tzinfo=timezone.utc).timestamp() * 1000)
BH = (-19.92, -43.94)

async def newpage(b, ctx=None):
    ctx = ctx or await b.new_context(viewport={'width': 1600, 'height': 720}, accept_downloads=True)
    pg = await ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
    await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(1300)
    return pg, errs

async def list_text(pg):
    return await pg.evaluate("document.querySelector('#gpxList').innerText.replace(/\\n/g,' | ')")

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')

        # ================= dia/noite pelo sol =================
        pg, errs = await newpage(b)
        r = await pg.evaluate('''([a,b,c,d])=>({noon:TN.sunElev(a,-19.92,-43.94),mid:TN.sunElev(b,-19.92,-43.94),polar:TN.sunElev(c,78,15),rise:(()=>{for(let m=0;m<24*60;m++){const e=TN.sunElev(d+m*60000,-19.92,-43.94);if(e>-0.833)return m}})(),set:(()=>{for(let m=24*60;m>0;m--){const e=TN.sunElev(d+m*60000,-19.92,-43.94);if(e>-0.833)return m}})()})''', [utc(15), utc(3), utc(12, 0, 15), utc(0)])
        check('sol a pino perto do meio-dia (BH, 15/11): ~88°', 85 < r['noon'] < 90, f"{r['noon']:.1f}°")
        check('sol bem abaixo do horizonte à meia-noite', r['mid'] < -30, f"{r['mid']:.1f}°")
        check('nascer do sol de BH entre 05:00 e 05:45 (hora local)', 8 * 60 <= r['rise'] <= 8 * 60 + 45, f"{r['rise'] // 60}:{r['rise'] % 60:02d} UTC")
        check('pôr do sol de BH entre 18:00 e 18:45 (hora local)', 21 * 60 <= r['set'] <= 21 * 60 + 45, f"{r['set'] // 60}:{r['set'] % 60:02d} UTC")
        # posição + hora controlam o tema no modo automático
        await pg.evaluate('([lat,lon])=>{TN.cfg.dayMode="auto";TN.onPos({timestamp:1e12,coords:{latitude:lat,longitude:lon,altitude:0,accuracy:5,speed:0,heading:null}})}', list(BH))
        await pg.evaluate('(t)=>{Date.now=()=>t;TN.autoTheme()}', utc(15))
        check('automático: dia ao meio-dia', await pg.evaluate("document.body.classList.contains('day')"))
        await pg.evaluate('(t)=>{Date.now=()=>t;TN.autoTheme()}', utc(3))
        check('automático: noite à meia-noite', await pg.evaluate("!document.body.classList.contains('day')"))
        await pg.evaluate('(t)=>{Date.now=()=>t;TN.autoTheme()}', utc(15))
        # botão cicla auto -> dia -> noite -> auto
        modos = []
        for _ in range(3):
            await pg.evaluate("document.querySelector('#bDay').click()"); modos.append(await pg.evaluate('TN.cfg.dayMode'))
        check('botão 🌗 cicla dia → noite → automático', modos == ['day', 'night', 'auto'], str(modos))
        await pg.evaluate("document.querySelector('#bDay').click()"); await pg.evaluate('(t)=>{Date.now=()=>t}', utc(3))
        await pg.evaluate('TN.autoTheme()')
        check('modo "dia" forçado ignora o sol', await pg.evaluate("document.body.classList.contains('day')"))
        await pg.context.close()

        # ================= gerenciador de GPX =================
        pg, errs = await newpage(b)
        await pg.evaluate("document.querySelector('#bGpx').click()"); await pg.wait_for_timeout(300)
        check('começa vazio', 'Pasta vazia' in await list_text(pg), await list_text(pg))
        await pg.click('#gNewDir'); await pg.fill('#askIn', 'Serra/Mantiqueira<b>'); await pg.click('#askOk'); await pg.wait_for_timeout(300)
        lt = await list_text(pg)
        check('nova pasta criada, nome higienizado (sem / < >)', 'Serra_Mantiqueira_b_' in lt, lt)
        await pg.set_input_files('#gImportIn', 't.gpx'); await pg.wait_for_timeout(400)
        await pg.set_input_files('#gImportIn', 't.gpx'); await pg.wait_for_timeout(400)
        lt = await list_text(pg)
        check('importar o mesmo arquivo duas vezes não sobrescreve ("t (2).gpx")', 't.gpx' in lt and 't (2).gpx' in lt, lt)
        await pg.click('[data-act=open][data-n="t.gpx"]'); await pg.wait_for_timeout(500)
        check('abrir carrega o GPX e fecha o diálogo', await pg.evaluate('TN.wps.length') == 3 and not await pg.evaluate("document.querySelector('#dlgGpx').open"))
        await pg.evaluate("document.querySelector('#bGpx').click()"); await pg.wait_for_timeout(300)
        await pg.click('[data-act=mv][data-n="t.gpx"]'); await pg.wait_for_timeout(200)
        opts = await pg.evaluate("[...document.querySelectorAll('#askSel option')].map(o=>o.textContent)")
        check('mover oferece as pastas existentes', any('Serra_Mantiqueira_b_' in o for o in opts), str(opts))
        await pg.select_option('#askSel', index=len(opts) - 1); await pg.click('#askOk'); await pg.wait_for_timeout(500)
        lt = await list_text(pg)
        check('arquivo saiu da raiz', 't.gpx' not in lt.replace('t (2).gpx', '') and 't (2).gpx' in lt, lt)
        await pg.click('[data-dir="Serra_Mantiqueira_b_"]'); await pg.wait_for_timeout(300)
        check('entrar na pasta mostra o arquivo movido', 't.gpx' in await list_text(pg), await list_text(pg))
        await pg.click('[data-act=ren][data-n="t.gpx"]'); await pg.fill('#askIn', 'trilha1.gpx'); await pg.click('#askOk'); await pg.wait_for_timeout(400)
        lt = await list_text(pg)
        check('renomear', 'trilha1.gpx' in lt and '📄 t.gpx' not in lt, lt)
        await pg.click('[data-act=open][data-n="trilha1.gpx"]'); await pg.wait_for_timeout(500)
        # reabre o app sem a cópia do localStorage: tem que voltar do armazenamento do gerenciador
        await pg.evaluate("localStorage.removeItem('tn_gpx')"); await pg.reload(); await pg.wait_for_timeout(1800)
        check('depois de recarregar, o GPX volta da pasta (sem o localStorage)', await pg.evaluate('TN.wps.length') == 3 and 'Serra' in await pg.evaluate("JSON.parse(localStorage.getItem('tn_gpxPath')).parts.join('/')"))
        await pg.evaluate("document.querySelector('#bGpx').click()"); await pg.wait_for_timeout(300)
        await pg.click('[data-dir="Serra_Mantiqueira_b_"]'); await pg.wait_for_timeout(300)
        await pg.click('#gSaveCur'); await pg.wait_for_timeout(400)
        check('"Guardar o GPX aberto aqui" cria cópia sem sobrescrever', 'trilha1 (2).gpx' in await list_text(pg), await list_text(pg))
        await pg.click('[data-act=rm][data-n="trilha1.gpx"]'); await pg.wait_for_timeout(200)
        check('apagar pede confirmação', await pg.evaluate("document.querySelector('#dlgAsk').open") and 'Não dá para desfazer' in await pg.evaluate("document.querySelector('#askMsg').textContent"))
        await pg.click('#askNo'); await pg.wait_for_timeout(200)
        check('cancelar mantém o arquivo', 'trilha1.gpx' in await list_text(pg))
        await pg.click('[data-act=rm][data-n="trilha1.gpx"]'); await pg.click('#askOk'); await pg.wait_for_timeout(400)
        check('confirmar apaga', 'trilha1.gpx' not in (await list_text(pg)).replace('trilha1 (2).gpx', ''), await list_text(pg))
        check('sem erros (gerenciador)', not errs, str(errs))
        await pg.context.close()

        # ================= notas e fotos =================
        img = os.path.join(TMP, 'foto.png'); Image.new('RGB', (3000, 2000), (200, 120, 30)).save(img)
        pg, errs = await newpage(b)
        await pg.evaluate("document.querySelector('#bNote').click()"); await pg.fill('#noteTx', 'sem gps'); await pg.click('#noteSave'); await pg.wait_for_timeout(200)
        check('sem GPS não salva a nota', len(await pg.evaluate('TN.rnotes')) == 0 and 'Sem GPS' in await pg.text_content('#toast'))
        await pg.click('#dlgNote [data-close]')
        await pg.evaluate('([lat,lon])=>TN.onPos({timestamp:Date.now(),coords:{latitude:lat,longitude:lon,altitude:900,accuracy:5,speed:0,heading:null}})', list(BH))
        await pg.evaluate("document.querySelector('#bNote').click()"); await pg.fill('#noteTx', '<img src=x onerror=window.__pwn=1> ponte quebrada'); await pg.set_input_files('#notePhIn', img); await pg.wait_for_timeout(900)
        info = await pg.text_content('#notePhInfo')
        check('foto de 3000×2000 reduzida e pronta (< 400 KB)', 'Foto pronta' in info and int(info.split('(')[1].split(' ')[0]) < 400, info)
        await pg.click('#noteSave'); await pg.wait_for_timeout(600)
        n = await pg.evaluate('TN.rnotes.map(n=>({t:n.text,photo:!!n.photo,lat:n.lat}))')
        check('nota salva com posição e foto', len(n) == 1 and n[0]['photo'] and abs(n[0]['lat'] - BH[0]) < 1e-6, str(n))
        lst = await pg.inner_text('#noteList')
        check('texto da nota aparece como texto (sem executar)', '<img src=x' in lst and await pg.evaluate('window.__pwn===undefined'), lst.replace('\n', ' | '))
        await pg.click('#dlgNote [data-close]')
        await pg.reload(); await pg.wait_for_timeout(1800)
        n = await pg.evaluate('TN.rnotes.map(n=>({photo:!!n.photo,url:!!n.url}))')
        check('depois de recarregar a nota e a foto continuam', n == [{'photo': True, 'url': True}], str(n))
        # --- exportar com foto: ZIP ---
        await pg.click('#bRec')
        await pg.evaluate('([lat,lon])=>{const t=Date.now();for(let i=0;i<8;i++)TN.onPos({timestamp:t+i*3000,coords:{latitude:lat,longitude:lon+i*0.0003,altitude:900,accuracy:5,speed:10,heading:90}})}', list(BH))
        await pg.evaluate("document.querySelector('#bSet').click()")
        async with pg.expect_download() as dl:
            await pg.click('#bExport')
        d = await dl.value; zpath = os.path.join(TMP, d.suggested_filename); await d.save_as(zpath)
        check('exportação com foto vem em .zip', zpath.endswith('.zip'), d.suggested_filename)
        z = zipfile.ZipFile(zpath)
        check('ZIP íntegro (CRC conferido pelo Python)', z.testzip() is None, str(z.namelist()))
        gname = [x for x in z.namelist() if x.endswith('.gpx')][0]; jname = [x for x in z.namelist() if x.startswith('fotos/') and x.endswith('.jpg')]
        check('ZIP tem o GPX e a foto', len(jname) == 1, str(z.namelist()))
        jpg = z.read(jname[0]); im = Image.open(__import__('io').BytesIO(jpg))
        check('a foto do ZIP é um JPEG válido de até 1280 px', jpg[:2] == b'\xff\xd8' and max(im.size) == 1280, str(im.size))
        root = ET.fromstring(z.read(gname)); ns = {'g': 'http://www.topografix.com/GPX/1/1'}
        wpts = root.findall('g:wpt', ns); trkpts = root.findall('.//g:trkpt', ns)
        check('GPX é XML válido, com os pontos de trilho gravados e a nota como waypoint', len(trkpts) >= 7 and len(wpts) == 1, f'{len(trkpts)} pts, {len(wpts)} wpt')
        desc = wpts[0].find('g:desc', ns).text; link = wpts[0].find('g:link', ns).get('href')
        check('descrição da nota preservada (escapada no XML) e link para a foto', desc.startswith('<img src=x') and link == jname[0], f'{desc!r} {link}')
        # --- cópia em Gravações ---
        await pg.click('#dlgSet [data-close]'); await pg.evaluate("document.querySelector('#bGpx').click()"); await pg.wait_for_timeout(400)
        check('cópia do GPX exportado ficou na pasta "Gravações"', 'Gravações' in await list_text(pg), await list_text(pg))
        await pg.click('#dlgGpx [data-close]')
        # --- limpar gravação ---
        await pg.evaluate("document.querySelector('#bSet').click()"); await pg.click('#bNewRec'); await pg.click('#askOk'); await pg.wait_for_timeout(500)
        check('limpar gravação apaga trilho e notas', await pg.evaluate('TN.rnotes.length') == 0)
        await pg.click('#dlgSet [data-close]')
        await pg.reload(); await pg.wait_for_timeout(1500)
        check('limpeza persiste depois de recarregar', await pg.evaluate('TN.rnotes.length') == 0)
        # --- exportar sem foto: .gpx puro ---
        await pg.evaluate('([lat,lon])=>TN.onPos({timestamp:Date.now(),coords:{latitude:lat,longitude:lon,altitude:900,accuracy:5,speed:0,heading:null}})', list(BH))
        await pg.evaluate("document.querySelector('#bNote').click()"); await pg.fill('#noteTx', 'só texto'); await pg.click('#noteSave'); await pg.wait_for_timeout(400); await pg.click('#dlgNote [data-close]')
        await pg.evaluate("document.querySelector('#bSet').click()")
        async with pg.expect_download() as dl:
            await pg.click('#bExport')
        d = await dl.value
        check('sem foto, a exportação continua sendo .gpx', d.suggested_filename.endswith('.gpx'), d.suggested_filename)
        check('sem erros (notas)', not errs, str(errs))
        await b.close()
    print('\nRESULTADO:', 'FALHOU ' + str(FAILS) if FAILS else 'tudo certo')
    sys.exit(1 if FAILS else 0)
asyncio.run(main())
