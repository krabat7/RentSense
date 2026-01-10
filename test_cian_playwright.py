import asyncio
from playwright.async_api import async_playwright
import sys

test_id = sys.argv[1] if len(sys.argv) > 1 else "311739319"

async def test_cian():
    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch(headless=True)
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        
        url = f"https://www.cian.ru/rent/flat/{test_id}/"
        print(f"Loading: {url}")
        
        await page.goto(url, wait_until="networkidle", timeout=30000)
        
        await asyncio.sleep(3)
        
        html = await page.content()
        
        print(f"Page loaded, HTML length: {len(html)}")
        
        if "Captcha" in html or "captcha" in html.lower():
            print("WARNING: Captcha detected")
        else:
            print("OK: No captcha")
        
        if '"offerData":' in html:
            print("SUCCESS: Found offerData!")
            import re
            import json
            
            from app.parser.tools import recjson
            pageJS = recjson(r'"offerData":\s*(\{.*?\})', html)
            
            if pageJS:
                print(f"Parsed JSON! Keys: {list(pageJS.keys())[:10]}")
                if 'offer' in pageJS:
                    offer = pageJS['offer']
                    print(f"  Offer ID: {offer.get('cianId')}")
                    print(f"  Price: {offer.get('priceTotalRur')}")
                    print(f"  Deal Type: {offer.get('dealType')}")
                    print(f"  Rooms: {offer.get('roomsCount')}")
                    print(f"  Area: {offer.get('totalArea')}")
                    
                    from app.parser.pagecheck import pagecheck
                    if data := pagecheck(pageJS):
                        print("\nSUCCESS: Data parsed successfully!")
                        print(f"  Parsed offer ID: {data.get('offers', {}).get('cian_id')}")
                        print(f"  Parsed price: {data.get('offers', {}).get('price')}")
                else:
                    print("  No 'offer' key in pageJS")
            else:
                print("Failed to parse JSON with recjson")
        else:
            print("FAILED: offerData not found")
            
            scripts = await page.evaluate("""
                () => {
                    const scripts = Array.from(document.querySelectorAll('script'));
                    return scripts.map(s => s.textContent).filter(s => s && s.length > 100);
                }
            """)
            
            print(f"Found {len(scripts)} script tags with content")
            for i, script in enumerate(scripts[:5]):
                if 'offer' in script.lower() or 'cian' in script.lower():
                    print(f"Script {i} contains offer/cian: {script[:200]}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_cian())

