import requests
import sys
from app.parser.tools import headers, proxyDict
import random

print("Testing proxy connections...")
print("=" * 50)

test_url = "http://httpbin.org/ip"

for i, (proxy, last_time) in enumerate(proxyDict.items(), 1):
    if not proxy:
        print(f"\n{i}. Testing without proxy (direct connection)...")
    else:
        print(f"\n{i}. Testing proxy: {proxy[:50]}...")
    
    try:
        response = requests.get(
            test_url,
            headers=random.choice(headers),
            proxies={'http': proxy, 'https': proxy} if proxy else None,
            timeout=10
        )
        if response.status_code == 200:
            print(f"  OK Status: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
        else:
            print(f"  FAILED Status: {response.status_code}")
    except Exception as e:
        print(f"  ERROR: {e}")

print("\n" + "=" * 50)
print("Testing Cian with proxies...")

test_id = "311739319"
url = f"https://www.cian.ru/rent/flat/{test_id}/"

for i, (proxy, last_time) in enumerate(proxyDict.items(), 1):
    if not proxy:
        continue
    
    print(f"\nTesting Cian with proxy {i}: {proxy[:50]}...")
    try:
        response = requests.get(
            url,
            headers=random.choice(headers),
            proxies={'http': proxy, 'https': proxy},
            timeout=15
        )
        print(f"  Status: {response.status_code}")
        print(f"  Length: {len(response.text)}")
        
        if response.status_code == 200:
            if "Captcha" in response.text or "captcha" in response.text.lower():
                print("  WARNING: Captcha detected")
            elif '"offerData":' in response.text:
                print("  SUCCESS: Found offerData!")
                break
            else:
                print("  INFO: No captcha, but offerData not found")
        elif response.status_code == 403:
            print("  ERROR: 403 Forbidden - proxy may be blocked")
        else:
            print(f"  ERROR: Status {response.status_code}")
    except Exception as e:
        print(f"  ERROR: {e}")

