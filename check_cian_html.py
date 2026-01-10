import requests
import sys
from app.parser.tools import headers
import random

test_id = sys.argv[1] if len(sys.argv) > 1 else "311739319"
url = f"https://www.cian.ru/rent/flat/{test_id}/"

print(f"Проверяю URL: {url}")
response = requests.get(url, headers=random.choice(headers), timeout=10)
print(f"Status code: {response.status_code}")

html = response.text

print("\n=== Поиск возможных JSON структур ===")
import re

patterns = [
    (r'"offerData":\s*(\{.*?\})', 'offerData'),
    (r'"offer":\s*(\{.*?\})', 'offer'),
    (r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', '__INITIAL_STATE__'),
    (r'window\.__SERVER_DATA__\s*=\s*(\{.*?\});', '__SERVER_DATA__'),
    (r'<script[^>]*>.*?(\{.*?"offer".*?\}).*?</script>', 'script with offer'),
    (r'data-options=["\'](\{.*?\})["\']', 'data-options'),
]

for pattern, name in patterns:
    matches = re.findall(pattern, html, re.DOTALL)
    if matches:
        print(f"OK Найден {name}: {len(matches)} совпадений")
        if len(matches[0]) < 500:
            print(f"  Пример: {matches[0][:200]}...")
    else:
        print(f"NOT FOUND {name}")

print("\n=== Поиск ключевых слов ===")
keywords = ['cianId', 'priceTotalRur', 'dealType', 'rent', 'sale', 'flat', 'offer']
for keyword in keywords:
    count = html.count(keyword)
    if count > 0:
        print(f"OK '{keyword}' найден {count} раз(а)")

print("\n=== Поиск script тегов с данными ===")
script_tags = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"Найдено {len(script_tags)} script тегов")
for i, script in enumerate(script_tags[:5]):
    if 'offer' in script.lower() or 'cian' in script.lower() or 'price' in script.lower():
        print(f"\nScript {i+1} (первые 300 символов):")
        print(script[:300])

print("\n=== Сохранение HTML для анализа ===")
with open(f'cian_page_{test_id}.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f"HTML сохранен в cian_page_{test_id}.html")

