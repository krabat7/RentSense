#!/usr/bin/env python3
import re

with open('app/parser/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Ищем проблемную строку
if "proxy = random.choice([k for k, v in proxyDict.items() if v <= time.time()])" in content:
    # Заменяем на исправленный код
    old_code = """    else:
        # Если все прокси заблокированы, используем случайный (fallback)
        proxy = random.choice([k for k, v in proxyDict.items() if v <= time.time()])"""
    
    new_code = """    else:
        # Если все прокси заблокированы после ожидания, используем пустой прокси (без прокси)
        # или выбираем тот, который освободится раньше всех
        if len(proxyDict) > 1:  # Есть прокси в словаре
            # Выбираем прокси с наименьшим временем блокировки (освободится раньше всех)
            earliest_proxy = min(proxyDict.items(), key=lambda x: x[1])
            if earliest_proxy[1] <= time.time() + 300:  # Если освободится в течение 5 минут
                proxy = earliest_proxy[0]
                logging.warning(f'All proxies blocked, using earliest available: {proxy[:30]}... (unlocks in {earliest_proxy[1] - time.time():.0f}s)')
            else:
                # Если все прокси заблокированы надолго, используем пустой прокси
                proxy = ''
                logging.warning('All proxies blocked for >5 minutes, using no proxy')
        else:
            # Нет прокси в словаре, используем пустой
            proxy = ''
            logging.warning('No proxies configured, using no proxy')"""
    
    content = content.replace(old_code, new_code)
    with open('app/parser/main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Исправление применено")
else:
    # Проверяем, может уже исправлено
    if "earliest_proxy = min(proxyDict.items()" in content:
        print("✓ Исправление уже применено")
    else:
        print("⚠ Проблемная строка не найдена, нужна ручная проверка")
