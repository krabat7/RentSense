import re

filename = 'cian_session_test_311739319.html'

with open(filename, 'r', encoding='utf-8') as f:
    html = f.read()

print(f"HTML length: {len(html)} characters")
print(f"Has 'cian': {'cian' in html.lower()[:5000]}")
print(f"Has 'script': {'<script' in html}")

scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"\nScripts found: {len(scripts)}")

for i, script in enumerate(scripts[:10]):
    if len(script) > 100:
        has_offer = 'offer' in script.lower()[:1000]
        has_cian = 'cian' in script.lower()[:1000]
        has_price = 'price' in script.lower()[:1000]
        if has_offer or has_cian or has_price:
            print(f"\nScript {i}: length={len(script)}, offer={has_offer}, cian={has_cian}, price={has_price}")
            if has_offer or has_cian:
                print(f"First 500 chars: {script[:500]}")

print("\n=== Searching for JSON patterns ===")
patterns = [
    (r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', '__INITIAL_STATE__'),
    (r'window\.__SERVER_DATA__\s*=\s*(\{.*?\});', '__SERVER_DATA__'),
    (r'JSON\.parse\(["\']([^"\']+)["\']\)', 'JSON.parse'),
    (r'\{[^{}]*"id"[^{}]*"311739319"[^{}]*\}', 'ID in object'),
]

for pattern, name in patterns:
    matches = re.findall(pattern, html, re.DOTALL)
    if matches:
        print(f"\n{name}: {len(matches)} matches")
        print(f"Example: {matches[0][:300]}")

