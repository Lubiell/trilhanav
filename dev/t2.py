import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        pg=await b.new_page(viewport={'width':1600,'height':720})
        errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
        await pg.goto('http://localhost:8765/index.html');await pg.wait_for_timeout(2000)
        await pg.set_input_files('#fileIn','rb.pdf');await pg.wait_for_timeout(2500)
        await pg.keyboard.press('ArrowDown');await pg.wait_for_timeout(600)
        print(await pg.evaluate('document.querySelector("#rb").scrollTop'), await pg.evaluate('document.querySelectorAll("#rb canvas").length'))
        await pg.evaluate("document.querySelector('#bSplit').click()");await pg.wait_for_timeout(800);await pg.screenshot(path='split.png')
        print(errs);await b.close()
asyncio.run(main())
