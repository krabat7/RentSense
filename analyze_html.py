import re
import json
import sys

test_id = sys.argv[1] if len(sys.argv) > 1 else "311739319"
filename = f'cian_page_{test_id}.html'

try:
    with open(filename, 'r', encoding='utf-8') as f:
        html = f.read()
except:
    print(f"File {filename} not found")
    sys.exit(1)

print(f"HTML length: {len(html)} characters")

scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"\nFound {len(scripts)} script tags")

for i, script in enumerate(scripts):
    if len(script) > 100:
        has_offer = 'offer' in script.lower()
        has_cian = 'cian' in script.lower()
        has_price = 'price' in script.lower()
        has_id = test_id in script
        if has_offer or has_cian or has_price or has_id:
            print(f"\nScript {i}: length={len(script)}, offer={has_offer}, cian={has_cian}, price={has_price}, id={has_id}")
            if has_offer or has_cian:
                print(f"First 500 chars: {script[:500]}")

print("\n=== Searching for JSON-like structures ===")
json_patterns = [
    (r'\{[^{}]*"id"[^{}]*' + test_id + r'[^{}]*\}', 'ID in object'),
    (r'\{[^{}]*"price"[^{}]*\}', 'price object'),
    (r'\{[^{}]*"offer"[^{}]*\}', 'offer object'),
]

for pattern, name in json_patterns:
    matches = re.findall(pattern, html, re.DOTALL)
    if matches:
        print(f"\n{name}: {len(matches)} matches")
        print(f"Example: {matches[0][:300]}")

print("\n=== Searching for API endpoints ===")
api_patterns = [
    r'https?://[^"\s]+api[^"\s]+',
    r'https?://[^"\s]+cian[^"\s]+offer[^"\s]+',
    r'/api/[^"\s]+',
]
for pattern in api_patterns:
    matches = re.findall(pattern, html)
    if matches:
        print(f"\nAPI endpoints found: {list(set(matches))[:5]}")

print("\n=== Searching for data attributes ===")
data_attrs = re.findall(r'data-[^=]*="[^"]*"', html)
if data_attrs:
    print(f"Found {len(data_attrs)} data attributes")
    for attr in data_attrs[:10]:
        if 'offer' in attr.lower() or 'cian' in attr.lower():
            print(f"  {attr[:100]}")

