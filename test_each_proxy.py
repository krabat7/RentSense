import requests
import time
from app.parser.tools import headers
import random

proxies = [
    ("PROXY1", "http://gPrh7mayd7:cDs82GsH8e@46.161.29.91:31638"),
    ("PROXY2", "http://gF5CdZ3tVh:WBF5P4a7uW@46.161.29.212:36095"),
    ("PROXY3", "http://Y34xbQACPJ:pQVJx66wc2@83.171.240.229:32844"),
]

test_url = "http://httpbin.org/ip"
cian_url = "https://www.cian.ru/rent/flat/311739319/"

full_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

print("=" * 70)
print("DETAILED PROXY TEST")
print("=" * 70)

results = []

for name, proxy in proxies:
    print(f"\n{'='*70}")
    print(f"Testing {name}: {proxy[:60]}...")
    print(f"{'='*70}")
    
    result = {
        'name': name,
        'proxy': proxy,
        'basic_test': None,
        'cian_test': None,
        'cian_status': None,
        'cian_has_captcha': None,
        'cian_has_offerdata': None,
    }
    
    # Test 1: Basic connectivity
    print("\n1. Basic connectivity test (httpbin.org/ip)...")
    try:
        response = requests.get(
            test_url,
            headers=random.choice(headers),
            proxies={'http': proxy, 'https': proxy},
            timeout=10
        )
        if response.status_code == 200:
            print(f"   OK SUCCESS: Status {response.status_code}")
            print(f"   Response: {response.text.strip()}")
            result['basic_test'] = True
        else:
            print(f"   FAILED: Status {response.status_code}")
            result['basic_test'] = False
    except Exception as e:
        print(f"   ERROR: {e}")
        result['basic_test'] = False
    
    time.sleep(1)
    
    # Test 2: Cian connection
    print("\n2. Cian connection test...")
    try:
        session = requests.Session()
        
        # First get main page for cookies
        print("   Getting main page for cookies...")
        main_response = session.get(
            "https://www.cian.ru",
            headers=full_headers,
            proxies={'http': proxy, 'https': proxy},
            timeout=10
        )
        print(f"   Main page status: {main_response.status_code}")
        time.sleep(2)
        
        # Then get offer page
        print(f"   Getting offer page...")
        cian_response = session.get(
            cian_url,
            headers=full_headers,
            proxies={'http': proxy, 'https': proxy},
            timeout=15
        )
        
        result['cian_status'] = cian_response.status_code
        result['cian_test'] = cian_response.status_code == 200
        
        print(f"   Status: {cian_response.status_code}")
        print(f"   Response length: {len(cian_response.text)} bytes")
        
        if cian_response.status_code == 200:
            html = cian_response.text
            has_captcha = "Captcha" in html or "captcha" in html.lower()
            has_offerdata = '"offerData":' in html
            
            result['cian_has_captcha'] = has_captcha
            result['cian_has_offerdata'] = has_offerdata
            
            if has_captcha:
                print("   WARNING: Captcha detected")
            else:
                print("   OK No captcha")
            
            if has_offerdata:
                print("   OK SUCCESS: offerData found!")
            else:
                print("   FAILED offerData not found")
                
            # Save response for analysis
            filename = f'cian_{name.lower()}_test.html'
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"   Saved to {filename}")
            
        elif cian_response.status_code == 403:
            print("   FAILED 403 Forbidden - Proxy blocked by Cian")
        else:
            print(f"   FAILED Error status: {cian_response.status_code}")
            
    except requests.exceptions.ProxyError as e:
        print(f"   PROXY ERROR: {e}")
        result['cian_test'] = False
    except requests.exceptions.Timeout:
        print(f"   TIMEOUT: Request timed out")
        result['cian_test'] = False
    except Exception as e:
        print(f"   ERROR: {e}")
        result['cian_test'] = False
    
    results.append(result)
    time.sleep(2)

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

for result in results:
    print(f"\n{result['name']}: {result['proxy'][:60]}")
    print(f"  Basic test: {'OK' if result['basic_test'] else 'FAILED'}")
    print(f"  Cian test: {'OK' if result['cian_test'] else 'FAILED'} (Status: {result['cian_status']})")
    if result['cian_has_captcha'] is not None:
        print(f"  Captcha: {'Yes' if result['cian_has_captcha'] else 'No'}")
    if result['cian_has_offerdata'] is not None:
        print(f"  offerData: {'Yes' if result['cian_has_offerdata'] else 'No'}")

print("\n" + "=" * 70)
print("WORKING PROXIES FOR CIAN:")
print("=" * 70)
working = [r for r in results if r['cian_test'] and r['cian_status'] == 200]
if working:
    for r in working:
        print(f"  OK {r['name']}: {r['proxy']}")
else:
    print("  FAILED None of the proxies work with Cian (all return 403 or other errors)")

print("\n" + "=" * 70)
print("PROXIES TO REPORT TO SUPPORT:")
print("=" * 70)
broken = [r for r in results if not r['basic_test'] or (r['cian_test'] is False and r['cian_status'] == 403)]
if broken:
    for r in broken:
        print(f"  FAILED {r['name']}: {r['proxy']}")
        if not r['basic_test']:
            print(f"    Reason: Basic connectivity failed")
        elif r['cian_status'] == 403:
            print(f"    Reason: 403 Forbidden from Cian")
else:
    print("  All proxies have basic connectivity, but may have issues with Cian")

