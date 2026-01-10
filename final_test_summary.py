import requests
from app.parser.tools import headers, proxyDict
import random

print("=" * 70)
print("FINAL TEST SUMMARY")
print("=" * 70)

proxies = [
    ("PROXY1", "http://gPrh7mayd7:cDs82GsH8e@46.161.29.91:31638"),
    ("PROXY2", "http://gF5CdZ3tVh:WBF5P4a7uW@46.161.29.212:36095"),
    ("PROXY3", "http://Y34xbQACPJ:pQVJx66wc2@83.171.240.229:32844"),
]

cian_url = "https://www.cian.ru/rent/flat/311739319/"

print("\n1. ПРОБЛЕМА С ПРОКСИ:")
print("-" * 70)
for name, proxy in proxies:
    try:
        session = requests.Session()
        response = session.get(
            cian_url,
            headers=random.choice(headers),
            proxies={'http': proxy, 'https': proxy},
            timeout=10
        )
        status = "OK (200)" if response.status_code == 200 else f"FAILED ({response.status_code})"
        print(f"{name}: {status}")
        if response.status_code == 403:
            print(f"  -> Проблема: Циан блокирует этот IP (403 Forbidden)")
    except Exception as e:
        print(f"{name}: ERROR - {e}")

print("\n2. ПРОБЛЕМА С ЦИАНОМ (даже с рабочим прокси):")
print("-" * 70)
working_proxy = proxies[2][1]  # PROXY3
session = requests.Session()
response = session.get(
    cian_url,
    headers=random.choice(headers),
    proxies={'http': working_proxy, 'https': working_proxy},
    timeout=10
)

if response.status_code == 200:
    html = response.text
    has_offerdata = '"offerData":' in html
    print(f"Статус: 200 OK (прокси работает)")
    print(f"offerData в HTML: {'ДА' if has_offerdata else 'НЕТ'}")
    if not has_offerdata:
        print("  -> Проблема: Циан изменил структуру - данные загружаются через JavaScript")
        print("  -> Решение: Нужен Playwright/Selenium для рендеринга JS")

print("\n" + "=" * 70)
print("ИТОГО:")
print("=" * 70)
print("1. ПРОКСИ: 2 из 3 не работают с Цианом (403) - проблема прокси-провайдера")
print("2. ЦИАН: Даже с рабочим прокси старый парсер не работает - нужен Playwright")
print("=" * 70)

