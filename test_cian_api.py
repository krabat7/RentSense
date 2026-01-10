import requests
import sys
import re
from app.parser.tools import headers
import random
import json

test_id = sys.argv[1] if len(sys.argv) > 1 else "311739319"

api_endpoints = [
    f"https://www.cian.ru/api/v1/offers/{test_id}/",
    f"https://api.cian.ru/v1/offers/{test_id}/",
    f"https://www.cian.ru/api/offers/{test_id}",
    f"https://www.cian.ru/rent/flat/{test_id}/?ajax=1",
    f"https://www.cian.ru/rent/flat/{test_id}/?format=json",
]

print(f"Testing API endpoints for offer {test_id}...\n")

for endpoint in api_endpoints:
    try:
        response = requests.get(endpoint, headers=random.choice(headers), timeout=5)
        print(f"{endpoint}")
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"  OK JSON response! Keys: {list(data.keys())[:10]}")
                if 'offer' in data or 'data' in data or 'result' in data:
                    print(f"  Contains offer/data/result!")
                    break
            except:
                if 'offer' in response.text.lower() or 'cian' in response.text.lower():
                    print(f"  Contains offer/cian in text (first 200 chars): {response.text[:200]}")
        print()
    except Exception as e:
        print(f"  Error: {e}\n")

print("\n=== Trying to find API in page source ===")
url = f"https://www.cian.ru/rent/flat/{test_id}/"
response = requests.get(url, headers=random.choice(headers), timeout=10)
html = response.text

api_patterns = [
    r'https?://[^"\s]+/api/[^"\s]+',
    r'https?://api[^"\s]+cian[^"\s]+',
    r'fetch\(["\']([^"\']+)["\']',
    r'axios\.(get|post)\(["\']([^"\']+)["\']',
]

for pattern in api_patterns:
    matches = re.findall(pattern, html)
    if matches:
        print(f"Found potential API calls: {list(set(matches))[:5]}")

