import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        ctx=await b.new_context(viewport={'width':1600,'height':720})
        pg=await ctx.new_page()
        errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
        await pg.goto('http://localhost:8765/index.html?trilha=1');await pg.wait_for_timeout(2000)
        await pg.set_input_files('#offIn',['small.pmtiles.part2','small.pmtiles.part1','small.pmtiles.part3']);await pg.wait_for_timeout(4000)
        print(await pg.text_content('#offInfo'))
        await pg.reload();await pg.wait_for_timeout(2500)
        print('after reload:',await pg.text_content('#offInfo'))
        await pg.click('[data-pane=paneMap]');await pg.evaluate('map.setView([-19.92,-43.94],15)');await pg.wait_for_timeout(3000)
        await pg.screenshot(path='off.png')
        print(errs);await b.close()
asyncio.run(main())
