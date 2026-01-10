#!/usr/bin/env python3
"""
Детальный тест прокси - проверяет, что именно возвращается
Можно запустить локально или на сервере
"""
import logging
import time
import random
from pathlib import Path
from dotenv import dotenv_values
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Загрузка прокси из .env
env_path = Path(__file__).parent / '.env'
env = dotenv_values(env_path)

# Берем первый прокси для теста
proxy_url = env.get('PROXY1') or env.get('PROXY2') or env.get('PROXY3')
if not proxy_url:
    print("ОШИБКА: Не найдены прокси в .env (PROXY1, PROXY2, PROXY3)")
    exit(1)

headers = [
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.90 Safari/537.36"},
]

# URL для теста - список объявлений (как в парсере)
URL = 'https://www.cian.ru/cat.php?deal_type=rent&offer_type=flat&p=1&region=1'

def test_proxy_detailed(proxy_url):
    """Детальный тест прокси с сохранением HTML"""
    print("=" * 80)
    print("ДЕТАЛЬНЫЙ ТЕСТ ПРОКСИ")
    print("=" * 80)
    print(f"Прокси: {proxy_url.split('@')[1] if '@' in proxy_url else proxy_url}")
    print(f"URL: {URL}")
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
                print(f"Используется прокси: {parsed.hostname}:{parsed.port}")
            else:
                print("Используется прямое подключение (без прокси)")
            
            context = browser.new_context(**context_options)
            page = context.new_page()
            
            try:
                print("Отправка запроса...")
                start_time = time.time()
                response = page.goto(URL, wait_until='domcontentloaded', timeout=45000)
                response_time = time.time() - start_time
                
                print(f"✓ Ответ получен за {response_time:.2f} сек")
                
                if response:
                    print(f"✓ HTTP статус: {response.status}")
                    print(f"✓ Финальный URL: {page.url}")
                else:
                    print("⚠️  Response object is None")
                
                time.sleep(3)  # Ждем загрузки контента
                html = page.content()
                
                print()
                print("=" * 80)
                print("АНАЛИЗ HTML")
                print("=" * 80)
                print(f"Размер HTML: {len(html):,} байт")
                print()
                
                # Проверка на captcha
                if len(html) < 50000:
                    print("⚠️  HTML слишком короткий (вероятно captcha или ошибка)")
                if 'captcha' in html.lower():
                    print("❌ Обнаружена CAPTCHA в HTML")
                else:
                    print("✓ CAPTCHA не обнаружена")
                
                # Поиск ключевых элементов
                print()
                print("Поиск ключевых элементов:")
                checks = {
                    '"pageview"': '"pageview"' in html or '"pageview",' in html,
                    '"pageview",': '"pageview",' in html,
                    '"offerData"': '"offerData":' in html,
                    'cian.ru': 'cian.ru' in html,
                    'products': '"products"' in html,
                    'cianId': '"cianId"' in html,
                }
                
                for key, found in checks.items():
                    status = "✓" if found else "✗"
                    print(f"  {status} {key}: {'найден' if found else 'не найден'}")
                
                # Поиск JSON структур
                print()
                print("Поиск JSON структур:")
                import re
                
                # Ищем pageview
                pageview_match = re.search(r'"pageview",?\s*(\{.*?\})', html, re.DOTALL)
                if pageview_match:
                    print(f"  ✓ Найден 'pageview' JSON (длина: {len(pageview_match.group(1))} символов)")
                    # Сохраняем фрагмент
                    json_preview = pageview_match.group(1)[:500]
                    print(f"    Превью: {json_preview}...")
                else:
                    print("  ✗ 'pageview' JSON не найден")
                
                # Ищем другие возможные структуры
                patterns = [
                    (r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', '__INITIAL_STATE__'),
                    (r'window\.__SERVER_DATA__\s*=\s*(\{.*?\});', '__SERVER_DATA__'),
                    (r'"products":\s*(\[.*?\])', 'products array'),
                ]
                
                for pattern, name in patterns:
                    match = re.search(pattern, html, re.DOTALL)
                    if match:
                        print(f"  ✓ Найден {name} (длина: {len(match.group(1))} символов)")
                    else:
                        print(f"  ✗ {name} не найден")
                
                # Сохранение HTML для анализа
                output_file = f'proxy_test_output_{int(time.time())}.html'
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(html)
                print()
                print(f"✓ HTML сохранен в: {output_file}")
                
                # Анализ первых 2000 символов
                print()
                print("Первые 2000 символов HTML:")
                print("-" * 80)
                print(html[:2000])
                print("-" * 80)
                
                # Итоговый вердикт
                print()
                print("=" * 80)
                print("ИТОГОВЫЙ ВЕРДИКТ")
                print("=" * 80)
                
                if response and response.status == 200:
                    if len(html) > 50000 and '"pageview"' in html:
                        print("✅ ПРОКСИ РАБОТАЕТ КОРРЕКТНО!")
                        print("   HTML содержит нужные данные для парсинга")
                    elif len(html) < 50000:
                        print("❌ ПРОКСИ ЗАБЛОКИРОВАН (captcha или ошибка)")
                        print(f"   HTML слишком короткий: {len(html)} байт")
                    elif '"pageview"' not in html:
                        print("⚠️  ПРОКСИ РАБОТАЕТ, НО СТРУКТУРА ИЗМЕНИЛАСЬ")
                        print("   HTML получен, но не содержит 'pageview'")
                        print("   Возможно, сайт изменил структуру или требуется другой подход")
                    else:
                        print("⚠️  НЕИЗВЕСТНАЯ ПРОБЛЕМА")
                elif response and response.status == 403:
                    print("❌ ПРОКСИ ЗАБЛОКИРОВАН (403 Forbidden)")
                elif response and response.status == 429:
                    print("❌ ПРОКСИ ЗАБЛОКИРОВАН (429 Too Many Requests)")
                else:
                    print(f"⚠️  НЕОЖИДАННЫЙ СТАТУС: {response.status if response else 'None'}")
                
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
    test_proxy_detailed(proxy_url)

