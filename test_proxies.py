#!/usr/bin/env python3
"""
Скрипт для тестирования прокси-серверов
Проверяет каждый прокси на доступность и возможность парсинга cian.ru
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

proxies = []
for i in range(1, 10):
    proxy = env.get(f'PROXY{i}')
    if proxy:
        proxies.append(proxy)

# Добавляем пустой прокси (без прокси)
proxies.append('')

headers = [
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.90 Safari/537.36"},
    {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Safari/605.1.15"},
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/118.0"},
]

URL = 'https://www.cian.ru/cat.php?deal_type=rent&offer_type=flat&p=1&region=1'

def test_proxy(proxy, proxy_name):
    """Тестирует один прокси"""
    result = {
        'proxy': proxy_name,
        'status': 'unknown',
        'response_time': None,
        'status_code': None,
        'html_length': None,
        'has_captcha': False,
        'has_offer_data': False,
        'error': None
    }
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            
            context_options = {
                'user_agent': random.choice(headers)['User-Agent'],
            }
            
            if proxy:
                parsed = urlparse(proxy)
                context_options['proxy'] = {
                    'server': f'{parsed.scheme}://{parsed.hostname}:{parsed.port}',
                    'username': parsed.username,
                    'password': parsed.password,
                }
            
            context = browser.new_context(**context_options)
            page = context.new_page()
            
            try:
                start_time = time.time()
                response = page.goto(URL, wait_until='domcontentloaded', timeout=45000)
                response_time = time.time() - start_time
                
                result['response_time'] = round(response_time, 2)
                
                if response:
                    result['status_code'] = response.status
                    
                    if response.status != 200:
                        result['status'] = 'error'
                        result['error'] = f'HTTP {response.status}'
                        return result
                
                time.sleep(2)  # Небольшая задержка для загрузки контента
                html = page.content()
                result['html_length'] = len(html)
                
                # Проверка на captcha
                if len(html) < 50000 and 'captcha' in html.lower():
                    result['has_captcha'] = True
                    result['status'] = 'blocked'
                    result['error'] = 'Captcha detected'
                elif response and response.status == 403:
                    result['status'] = 'blocked'
                    result['error'] = '403 Forbidden'
                elif response and response.status == 429:
                    result['status'] = 'blocked'
                    result['error'] = '429 Too Many Requests'
                elif '"offerData":' in html or '"pageview"' in html:
                    result['has_offer_data'] = True
                    result['status'] = 'working'
                elif len(html) < 100000:
                    result['status'] = 'suspicious'
                    result['error'] = 'HTML too short, no offerData found'
                else:
                    result['status'] = 'working'
                    result['has_offer_data'] = True
                
            finally:
                page.close()
                context.close()
                browser.close()
                
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
    
    return result

def main():
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ ПРОКСИ-СЕРВЕРОВ")
    print("=" * 80)
    print(f"Найдено прокси: {len(proxies)}")
    print(f"URL для теста: {URL}")
    print("=" * 80)
    print()
    
    results = []
    
    for i, proxy in enumerate(proxies, 1):
        proxy_name = f"PROXY{i}" if proxy else "NO PROXY"
        print(f"[{i}/{len(proxies)}] Тестирование {proxy_name}...", end=" ", flush=True)
        
        if proxy:
            # Маскируем пароль в выводе
            masked_proxy = proxy.split('@')[1] if '@' in proxy else proxy
            print(f"({masked_proxy})")
        else:
            print("(прямое подключение)")
        
        result = test_proxy(proxy, proxy_name)
        results.append(result)
        
        # Вывод результата
        status_emoji = {
            'working': '✅',
            'blocked': '❌',
            'error': '⚠️',
            'suspicious': '⚠️',
            'unknown': '❓'
        }
        
        emoji = status_emoji.get(result['status'], '❓')
        print(f"  {emoji} Статус: {result['status'].upper()}")
        
        if result['response_time']:
            print(f"  ⏱  Время ответа: {result['response_time']} сек")
        
        if result['status_code']:
            print(f"  📊 HTTP код: {result['status_code']}")
        
        if result['html_length']:
            print(f"  📄 Размер HTML: {result['html_length']:,} байт")
        
        if result['has_captcha']:
            print(f"  🚫 Обнаружена CAPTCHA")
        
        if result['has_offer_data']:
            print(f"  ✅ Найдены данные объявлений")
        
        if result['error']:
            print(f"  ⚠️  Ошибка: {result['error']}")
        
        print()
        
        # Небольшая задержка между тестами
        if i < len(proxies):
            time.sleep(2)
    
    # Итоговая статистика
    print("=" * 80)
    print("ИТОГОВАЯ СТАТИСТИКА")
    print("=" * 80)
    
    working = sum(1 for r in results if r['status'] == 'working')
    blocked = sum(1 for r in results if r['status'] == 'blocked')
    errors = sum(1 for r in results if r['status'] == 'error')
    suspicious = sum(1 for r in results if r['status'] == 'suspicious')
    
    print(f"✅ Работают: {working}/{len(results)}")
    print(f"❌ Заблокированы: {blocked}/{len(results)}")
    print(f"⚠️  Ошибки: {errors}/{len(results)}")
    print(f"⚠️  Подозрительные: {suspicious}/{len(results)}")
    print()
    
    if working > 0:
        print("Рабочие прокси:")
        for r in results:
            if r['status'] == 'working':
                print(f"  ✅ {r['proxy']}")
    else:
        print("⚠️  НЕТ РАБОЧИХ ПРОКСИ!")
        print("   Все прокси заблокированы или недоступны.")
        print("   Рекомендуется:")
        print("   1. Обновить список прокси")
        print("   2. Проверить доступность прокси-серверов")
        print("   3. Увеличить задержки между запросами")
    
    print("=" * 80)

if __name__ == "__main__":
    main()
