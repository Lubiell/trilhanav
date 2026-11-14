import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--ignore-certificate-errors'])
        pg=await b.new_page(viewport={'width':1600,'height':720})
        errs=[];pg.on('pageerror',lambda e:errs.append(str(e)));pg.on('console',lambda m:m.type=='error' and errs.append(m.text))
        await pg.goto('http://localhost:8765/index.html');await pg.wait_for_timeout(2500)
        await pg.set_input_files('#fileIn','t.gpx');await pg.wait_for_timeout(800)
        # simular GPS manual pelos pontos
        r=await pg.evaluate('''()=>{const t=Date.now();for(let i=0;i<=100;i++){const lat=-23.55+i*0.0003*0.99,lon=-46.63+i*0.0002*0.99;TN.onPos({timestamp:t+i*2000,coords:{latitude:lat,longitude:lon,altitude:800,accuracy:5,speed:null,heading:null}})}
          return {total:TN.st.total,wp:TN.st.wpIdx,state:TN.wpState,cap:document.querySelector('#cap').textContent,spd:document.querySelector('#speed').textContent}}''')
        print(r)
        # fora da trilha
        await pg.evaluate('()=>{TN.cfg.off=100;TN.onPos({timestamp:Date.now()+999999,coords:{latitude:-23.53,longitude:-46.60,altitude:800,accuracy:5,speed:10,heading:90}})}')
        print('banner',await pg.text_content('#banner'),await pg.is_visible('#banner'))
        await pg.keyboard.press('ArrowRight');await pg.keyboard.press('Enter')
        print('keys',await pg.text_content('#total'),await pg.text_content('#partial'))
        await pg.click('[data-pane=paneMap]');await pg.wait_for_timeout(1500);await pg.screenshot(path='map.png')
        await pg.click('[data-pane=paneDash]');await pg.wait_for_timeout(300);await pg.screenshot(path='dash.png')
        await pg.click('#bSet');await pg.wait_for_timeout(300);await pg.screenshot(path='set.png')
        await pg.click('[data-close]');
        await pg.set_viewport_size({'width':420,'height':860});await pg.click('[data-pane=paneRb]');await pg.wait_for_timeout(300);await pg.screenshot(path='port.png')
        print('errs',errs)
        await b.close()
asyncio.run(main())
