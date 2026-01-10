import requests
import sys
import time
from app.parser.tools import headers, proxyDict
import random
import re
import json

test_id = sys.argv[1] if len(sys.argv) > 1 else "311739319"

print(f"Testing Cian with session and proxy for offer {test_id}...")
print("=" * 50)

session = requests.Session()

full_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
}

proxy = "http://Y34xbQACPJ:pQVJx66wc2@83.171.240.229:32844"

print("Step 1: Getting main page to get cookies...")
try:
    main_page = session.get(
        "https://www.cian.ru",
        headers=full_headers,
        proxies={'http': proxy, 'https': proxy},
        timeout=10
    )
    print(f"Main page status: {main_page.status_code}")
    print(f"Cookies: {list(session.cookies.keys())}")
    time.sleep(2)
except Exception as e:
    print(f"Error getting main page: {e}")
    sys.exit(1)

print(f"\nStep 2: Getting offer page {test_id}...")
url = f"https://www.cian.ru/rent/flat/{test_id}/"

try:
    response = session.get(
        url,
        headers=full_headers,
        proxies={'http': proxy, 'https': proxy},
        timeout=15
    )
    
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"Response length: {len(response.text)}")
    
    html = response.text
    
    if "Captcha" in html or "captcha" in html.lower():
        print("\nWARNING: Captcha detected!")
    else:
        print("\nNo captcha detected!")
    
    if '"offerData":' in html:
        print("SUCCESS: Found 'offerData' in response!")
        match = re.search(r'"offerData":\s*(\{.*?\})', html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                print(f"Parsed JSON! Keys: {list(data.keys())[:10]}")
                if 'offer' in data:
                    offer = data['offer']
                    print(f"  Offer ID: {offer.get('cianId')}")
                    print(f"  Price: {offer.get('priceTotalRur')}")
                    print(f"  Deal Type: {offer.get('dealType')}")
            except Exception as e:
                print(f"Failed to parse JSON: {e}")
    else:
        print("FAILED: 'offerData' not found in response")
        
        with open(f'cian_session_test_{test_id}.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"Saved response to cian_session_test_{test_id}.html")
        
except Exception as e:
    print(f"Error: {e}")

