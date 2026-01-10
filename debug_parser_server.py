#!/usr/bin/env python3
"""
Скрипт для детального анализа работы парсера на сервере
Сохраняет HTML и анализирует, что именно возвращается
"""
import logging
import time
import random
from pathlib import Path
from dotenv import dotenv_values
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse
import re

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Загрузка прокси из .env
env_path = Path(__file__).parent / '.env'
env = dotenv_values(env_path)

proxyDict = {
    proxy: 0.0
    for proxy in (env.get(f'PROXY{i}') for i in range(1, 11)) if proxy
}

headers = [
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.90 Safari/537.36"},
]

URL = 'https://www.cian.ru/cat.php?deal_type=rent&offer_type=flat&p=1&region=1'

def debug_get_response(proxy_url=None):
    """Детальная отладка getResponse"""
    print("=" * 80)
    print("ДЕТАЛЬНАЯ ОТЛАДКА ПАРСЕРА")
    print("=" * 80)
    print(f"URL: {URL}")
    if proxy_url:
        print(f"Прокси: {proxy_url.split('@')[1] if '@' in proxy_url else proxy_url}")
    else:
        print("Прокси: нет (прямое подключение)")
    print("=" * 80)
    print()
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            
            context_options = {
                'user_agent': random.choice(headers)['User-Agent'],
            }
            
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
                print("Отправка запроса через Playwright...")
                start = time.time()
                response_obj = page.goto(URL, wait_until='domcontentloaded', timeout=45000)
                print(f"✓ Запрос выполнен за {time.time() - start:.2f} сек")
                
                if response_obj:
                    print(f"✓ HTTP статус: {response_obj.status}")
                else:
                    print("⚠️  Response object is None")
                
                time.sleep(5)
                html = page.content()
                current_url = page.url
                
                print(f"✓ HTML получен: {len(html):,} байт")
                print(f"✓ Финальный URL: {current_url}")
                print()
                
                # Проверки как в getResponse
                print("Проверки (как в getResponse):")
                print("-" * 80)
                
                # Проверка 1: Redirect
                if 'cian.ru' not in current_url:
                    print("❌ Redirected away from cian.ru")
                    print(f"   URL: {current_url}")
                else:
                    print("✓ URL корректный (cian.ru)")
                
                # Проверка 2: offerData (для страницы объявления)
                if '"offerData":' in html:
                    print("✓ Найден 'offerData' (для страницы объявления)")
                else:
                    print("✗ 'offerData' не найден (нормально для списка страниц)")
                
                # Проверка 3: Captcha
                if len(html) < 50000 and 'captcha' in html.lower():
                    print(f"❌ Captcha detected: HTML слишком короткий ({len(html)} байт)")
                else:
                    print(f"✓ Captcha не обнаружена (HTML: {len(html)} байт)")
                
                # Проверка 4: pageview для списка страниц
                if len(html) < 50000:
                    print(f"❌ HTML слишком короткий для списка страниц: {len(html)} байт")
                else:
                    print(f"✓ HTML достаточно большой: {len(html)} байт")
                
                if '"pageview"' not in html and '"pageview",' not in html:
                    print("❌ 'pageview' не найден в HTML")
                    print("   Это причина 'Recjson not match'!")
                else:
                    print("✓ 'pageview' найден в HTML")
                
                print("-" * 80)
                print()
                
                # Детальный поиск pageview
                print("Детальный поиск 'pageview':")
                print("-" * 80)
                
                # Ищем все вхождения
                pageview_positions = []
                for match in re.finditer(r'pageview', html, re.IGNORECASE):
                    start = max(0, match.start() - 100)
                    end = min(len(html), match.end() + 100)
                    context = html[start:end]
                    pageview_positions.append((match.start(), context))
                
                if pageview_positions:
                    print(f"✓ Найдено {len(pageview_positions)} вхождений 'pageview':")
                    for i, (pos, ctx) in enumerate(pageview_positions[:3], 1):
                        print(f"  {i}. Позиция {pos}: ...{ctx}...")
                else:
                    print("✗ 'pageview' не найден нигде в HTML")
                
                print("-" * 80)
                print()
                
                # Сохранение HTML
                timestamp = int(time.time())
                output_file = f'/tmp/debug_parser_{timestamp}.html'
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(html)
                print(f"✓ HTML сохранен в: {output_file}")
                print(f"  Размер: {len(html):,} байт")
                print()
                
                # Анализ структуры
                print("Анализ структуры HTML:")
                print("-" * 80)
                print(f"Содержит 'script': {html.count('<script')} тегов")
                print(f"Содержит 'div': {html.count('<div')} тегов")
                print(f"Содержит 'json': {html.lower().count('json')} раз")
                print(f"Содержит 'cian': {html.lower().count('cian')} раз")
                print(f"Содержит 'rent': {html.lower().count('rent')} раз")
                print(f"Содержит 'flat': {html.lower().count('flat')} раз")
                
                # Поиск возможных JSON структур
                print()
                print("Поиск возможных JSON структур:")
                patterns = [
                    (r'"pageview",?\s*(\{.*?\})', 'pageview JSON'),
                    (r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', '__INITIAL_STATE__'),
                    (r'window\.__SERVER_DATA__\s*=\s*(\{.*?\});', '__SERVER_DATA__'),
                    (r'"products":\s*(\[.*?\])', 'products array'),
                ]
                
                for pattern, name in patterns:
                    match = re.search(pattern, html, re.DOTALL)
                    if match:
                        json_len = len(match.group(1))
                        print(f"  ✓ {name}: найден (длина JSON: {json_len:,} символов)")
                        if json_len < 1000:
                            print(f"    Превью: {match.group(1)[:200]}...")
                    else:
                        print(f"  ✗ {name}: не найден")
                
                print("-" * 80)
                print()
                
                # Итоговый вывод
                print("=" * 80)
                print("ВЫВОД")
                print("=" * 80)
                
                if response_obj and response_obj.status == 200:
                    if len(html) > 50000 and ('"pageview"' in html or '"pageview",' in html):
                        print("✅ ВСЕ ОК: HTML содержит нужные данные")
                        print("   Проблема может быть в парсинге JSON (recjson)")
                    elif len(html) < 50000:
                        print("❌ ПРОБЛЕМА: HTML слишком короткий (captcha/блокировка)")
                    elif '"pageview"' not in html:
                        print("❌ ПРОБЛЕМА: HTML не содержит 'pageview'")
                        print("   Возможно, структура сайта изменилась")
                        print("   Или прокси возвращает неполный HTML")
                    else:
                        print("⚠️  ЧАСТИЧНО: HTML получен, но структура может отличаться")
                else:
                    status = response_obj.status if response_obj else 'None'
                    print(f"❌ ПРОБЛЕМА: HTTP статус {status}")
                
                print("=" * 80)
                
            finally:
                page.close()
                context.close()
                browser.close()
                
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Тестируем первый доступный прокси
    proxy = list(proxyDict.keys())[0] if proxyDict else None
    if proxy and proxy != '':
        debug_get_response(proxy)
    else:
        print("Прокси не найдены, тестируем без прокси...")
        debug_get_response(None)

