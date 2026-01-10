from playwright.sync_api import sync_playwright
import time

proxies = [
    ("PROXY4", "http://Tz8am3:EY5U7F@209.127.142.50:9709"),
    ("PROXY5", "http://Tz8am3:EY5U7F@168.196.238.113:9267"),
]

test_url = "https://www.cian.ru/rent/flat/311739319/"

print("Testing new Canadian proxies...")
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
            response = page.goto(test_url, wait_until='domcontentloaded', timeout=45000)
            time.sleep(5)
            html = page.content()
            current_url = page.url
            
            if response:
                print(f"  Status: {response.status}")
            else:
                print(f"  Status: No response object")
            
            print(f"  URL: {current_url[:60]}...")
            print(f"  HTML length: {len(html)}")
            
            if 'cian.ru' not in current_url or 'captcha' in current_url.lower():
                print(f"  WARNING: Redirected to captcha/login page")
            elif 'captcha' in html.lower() and len(html) < 50000:
                print(f"  WARNING: Captcha detected in page")
            elif '"offerData":' in html:
                print(f"  SUCCESS: offerData found! Length: {len(html)}")
                print(f"  Working proxy!")
            elif len(html) > 100000:
                print(f"  INFO: Large HTML ({len(html)}), may contain data")
            else:
                print(f"  INFO: HTML too short, may be error page")
                
        except Exception as e:
            print(f"  ERROR: {e}")
        finally:
            page.close()
            context.close()
        
        time.sleep(2)
    
    browser.close()

print("\n" + "=" * 70)
print("Test completed!")

