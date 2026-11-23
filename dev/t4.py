import asyncio,os
from playwright.async_api import async_playwright
BASE='https://raw.githubusercontent.com/Lubiell/trilhanav/mapas/mg/'
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        ctx=await b.new_context(viewport={'width':1600,'height':720})
        pg=await ctx.new_page()
        errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
        reqs=[];mode={'fail':'small.pmtiles.part2','corrupt':None}
        async def handler(route):
            name=route.request.url.split('/')[-1];reqs.append(name)
            if name==mode['fail']: await route.abort();return
            body=open('dl/'+name,'rb').read()
            if name==mode['corrupt']: body=body[:-1]+bytes([body[-1]^1])
            await route.fulfill(status=200,body=body,headers={'access-control-allow-origin':'*','content-type':'application/octet-stream'})
        await pg.route(BASE+'*',handler)
        await pg.goto('http://localhost:8765/index.html');await pg.wait_for_timeout(1500)
        await pg.evaluate('dlRetryMs=100')
        # 1) falha na parte 2 -> interrompido
        await pg.evaluate('downloadMap()');await pg.wait_for_timeout(1500)
        print('1 interrompido:',await pg.text_content('#offInfo'));print('  reqs',reqs)
        # 2) recarrega: mostra download incompleto
        await pg.reload();await pg.wait_for_timeout(1500);await pg.evaluate('dlRetryMs=100')
        print('2 apos recarregar:',await pg.text_content('#offInfo'))
        # 3) parte corrompida
        reqs.clear();mode['fail']=None;mode['corrupt']='small.pmtiles.part3'
        await pg.evaluate('downloadMap()');await pg.wait_for_timeout(2500)
        print('3 corrompida:',await pg.text_content('#offInfo'));print('  reqs',reqs)
        # 4) retoma e conclui: só as partes que faltam
        reqs.clear();mode['corrupt']=None
        await pg.evaluate('downloadMap()');await pg.wait_for_timeout(2500)
        print('4 concluido:',await pg.text_content('#offInfo'));print('  reqs',reqs)
        # 5) persiste e desenha
        await pg.reload();await pg.wait_for_timeout(2000)
        print('5 apos recarregar:',await pg.text_content('#offInfo'))
        await pg.click('[data-pane=paneMap]');await pg.evaluate('map.setView([-19.92,-43.94],15)');await pg.wait_for_timeout(3000)
        await pg.screenshot(path='dl.png')
        # 6) remover
        await pg.evaluate('document.querySelector("#bOffDel").click()');await pg.wait_for_timeout(800)
        print('6 removido:',await pg.text_content('#offInfo'), await pg.evaluate('(async()=>{const d=await navigator.storage.getDirectory();const n=[];for await(const k of d.keys())n.push(k);return n})()'))
        print('errs',errs);await b.close()
asyncio.run(main())
