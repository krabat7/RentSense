#!/usr/bin/env python3
import re
import glob
from playwright.sync_api import sync_playwright
from dotenv import dotenv_values
from pathlib import Path
from urllib.parse import urlparse
import random
import time

env_path = Path('/app/.env')
env = dotenv_values(env_path)
proxy_url = env.get('PROXY1')

headers = [{"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}]
URL = 'https://www.cian.ru/cat.php?deal_type=rent&offer_type=flat&p=1&region=1'

# Пробуем найти сохраненный HTML
html_files = glob.glob('/tmp/debug_parser_*.html')
if html_files:
    print(f"Используем сохраненный файл: {html_files[0]}")
    with open(html_files[0], 'r', encoding='utf-8') as f:
        html = f.read()
else:
    print("Делаем новый запрос...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context_options = {'user_agent': random.choice(headers)['User-Agent']}
        
        if proxy_url:
            parsed = urlparse(proxy_url)
            context_options['proxy'] = {
                'server': f'{parsed.scheme}://{parsed.hostname}:{parsed.port}',
                'username': parsed.username,
                'password': parsed.password,
            }
        
        context = browser.new_context(**context_options)
        page = context.new_page()
        try:
            page.goto(URL, wait_until='domcontentloaded', timeout=45000)
            time.sleep(5)
            html = page.content()
        finally:
            page.close()
            context.close()
            browser.close()

print("=" * 80)
print(f"Размер HTML: {len(html):,} байт")
print()

# Текущий паттерн
current_pattern = r'"pageview",\s*(\{.*?\})'
print(f"1. Текущий паттерн: {current_pattern}")
match = re.search(current_pattern, html, re.DOTALL)
if match:
    print("   ✓ НАЙДЕН!")
    print(f"   Длина: {len(match.group(1))} символов")
else:
    print("   ✗ НЕ НАЙДЕН")
print()

# Альтернативные паттерны
print("2. Альтернативные паттерны:")
patterns = [
    (r'"pageview"\s*,\s*(\{.*?\})', 'pageview без запятой внутри'),
    (r'["\']pageview["\']\s*,\s*(\{.*?\})', 'pageview с любыми кавычками'),
    (r'a\.ca\(["\']pageview["\'],\s*(\{.*?\})', 'a.ca("pageview", {...})'),
    (r'pageview.*?(\{.*?"page".*?\})', 'pageview с объектом page'),
]

for pattern, desc in patterns:
    match = re.search(pattern, html, re.DOTALL)
    if match:
        print(f"   ✓ {desc}: НАЙДЕН!")
        json_str = match.group(1)
        print(f"     Длина: {len(json_str):,} символов")
        if len(json_str) < 2000:
            print(f"     Превью: {json_str[:500]}...")
    else:
        print(f"   ✗ {desc}: не найден")
print()

# Поиск объекта с "page"
print("3. Поиск объектов с ключом 'page':")
page_pattern = r'"page"\s*:\s*(\{.*?\})'
matches = list(re.finditer(page_pattern, html, re.DOTALL))
if matches:
    print(f"   ✓ Найдено {len(matches)} объектов")
    for i, m in enumerate(matches[:3], 1):
        start = m.start(1)
        end = start + 1
        brackets = 1
        while brackets > 0 and end < len(html):
            if html[end] == '{':
                brackets += 1
            elif html[end] == '}':
                brackets -= 1
            end += 1
        
        full_json = html[start:end]
        print(f"   {i}. Длина: {len(full_json):,} символов")
        
        if '"pageNumber"' in full_json or '"products"' in full_json:
            print(f"      ✓ Содержит нужные поля!")
            print(f"      Превью: {full_json[:800]}...")
            print()
            print("      === ПОЛНЫЙ JSON (первые 3000 символов) ===")
            print(full_json[:3000])
            if len(full_json) > 3000:
                print("      ... (обрезано)")
            print("      ===========================================")
            print()
else:
    print("   ✗ Объекты с 'page' не найдены")
print()

# Поиск контекста pageview
print("4. Контекст вокруг 'pageview':")
pageview_matches = list(re.finditer(r'pageview', html, re.IGNORECASE))
if pageview_matches:
    for i, m in enumerate(pageview_matches[:2], 1):
        start = max(0, m.start() - 200)
        end = min(len(html), m.end() + 500)
        context = html[start:end]
        print(f"   {i}. Позиция {m.start()}:")
        print(f"      ...{context}...")
        print()
