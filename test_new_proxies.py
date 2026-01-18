#!/usr/bin/env python3
"""Простой тест новых прокси"""
import requests

PROXIES = [
    ("158.46.182.34:8000:PT9p16:nNmkU8", "Армения"),
    ("91.233.20.141:8000:MFDsV2:geHwTP", "Таджикистан"),
    ("46.19.71.145:8000:9D1pZg:a5YoGL", "Казахстан"),
    ("147.45.86.232:8000:ftXS76:q5P4rE", "Беларусь"),
    ("195.64.101.45:8000:f0muLE:KP4hV2", "Россия"),
]

print("="*60)
print("ТЕСТ НОВЫХ ПРОКСИ К CIAN.RU")
print("="*60)

results = []

for proxy_str, country in PROXIES:
    parts = proxy_str.split(':')
    host, port, user, pwd = parts
    proxy_url = f"http://{user}:{pwd}@{host}:{port}"
    
    print(f"\nТест: {host} ({country})")
    print("-" * 60)
    
    try:
        url = "https://www.cian.ru/cat.php?deal_type=rent&offer_type=flat&p=1&region=1"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        print("  Отправка запроса...", end=' ', flush=True)
        resp = requests.get(url, proxies={"http": proxy_url, "https": proxy_url}, 
                           headers=headers, timeout=10)
        
        print(f"Статус: {resp.status_code}")
        
        if resp.status_code == 200:
            content = resp.text.lower()
            if 'captcha' in content or 'капча' in content:
                print("  [FAIL] CAPTCHA обнаружена")
                results.append((host, country, False))
            elif 'cardcomponent' in content or 'объявлени' in content:
                print("  [OK] УСПЕХ! Страница загружена, объявления найдены")
                results.append((host, country, True))
            else:
                print("  [WARN] Страница загружена, но структура необычная")
                results.append((host, country, False))
        elif resp.status_code == 403:
            print("  [FAIL] 403 Forbidden - прокси заблокирован")
            results.append((host, country, False))
        else:
            print(f"  [FAIL] Неожиданный статус: {resp.status_code}")
            results.append((host, country, False))
            
    except requests.exceptions.Timeout:
        print("  [FAIL] Таймаут подключения")
        results.append((host, country, False))
    except requests.exceptions.ProxyError as e:
        print(f"  [FAIL] Ошибка прокси: {str(e)[:60]}")
        results.append((host, country, False))
    except Exception as e:
        print(f"  [FAIL] Ошибка: {type(e).__name__}: {str(e)[:60]}")
        results.append((host, country, False))

print(f"\n{'='*60}")
print("ИТОГИ")
print(f"{'='*60}")

working = [r for r in results if r[2]]
failed = [r for r in results if not r[2]]

for ip, country, success in results:
    status = "[OK] РАБОТАЕТ" if success else "[FAIL] НЕ РАБОТАЕТ"
    print(f"{ip} ({country}): {status}")

print(f"\nРаботающих: {len(working)}/{len(results)}")
print(f"Не работающих: {len(failed)}/{len(results)}")

if working:
    print("\n[OK] Работающие прокси:")
    for ip, country, _ in working:
        print(f"  - {ip} ({country})")

if failed:
    print("\n[FAIL] Не работающие прокси:")
    for ip, country, _ in failed:
        print(f"  - {ip} ({country})")

