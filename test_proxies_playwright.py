from playwright.sync_api import sync_playwright
import time

proxies = [
    ("PROXY1", "http://gPrh7mayd7:cDs82GsH8e@46.161.29.91:31638"),
    ("PROXY2", "http://gF5CdZ3tVh:WBF5P4a7uW@46.161.29.212:36095"),
    ("PROXY3", "http://Y34xbQACPJ:pQVJx66wc2@83.171.240.229:32844"),
]

test_url = "https://www.cian.ru/rent/flat/311739319/"

print("Testing proxies with Playwright (as in parser)...")
print("=" * 70)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    for name, proxy_url in proxies:
        print(f"\n{name}: {proxy_url[:60]}...")
        
        from urllib.parse import urlparse
        parsed = urlparse(proxy_url)
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            proxy={
                'server': f'{parsed.scheme}://{parsed.hostname}:{parsed.port}',
                'username': parsed.username,
                'password': parsed.password,
            }
        )
        
        page = context.new_page()
        
        try:
            response = page.goto(test_url, wait_until='domcontentloaded', timeout=30000)
            time.sleep(3)
            html = page.content()
            current_url = page.url
            
            if response:
                print(f"  Status: {response.status}")
            else:
                print(f"  Status: No response object")
            
            print(f"  URL: {current_url[:60]}...")
            print(f"  HTML length: {len(html)}")
            
            if 'cian.ru' not in current_url:
                print(f"  FAILED: Redirected away")
            elif 'captcha' in html.lower() and len(html) < 50000:
                print(f"  WARNING: Captcha detected")
            elif '"offerData":' in html:
                print(f"  SUCCESS: offerData found!")
            else:
                print(f"  INFO: No offerData (may need more wait time)")
                
        except Exception as e:
            print(f"  ERROR: {e}")
        finally:
            page.close()
            context.close()
        
        time.sleep(2)
    
    browser.close()

print("\n" + "=" * 70)
print("Test completed!")

