#!/usr/bin/env python3
"""
Скрипт для применения оптимизаций парсера на сервере
"""

import re
import sys

def apply_optimizations():
    # 1. Оптимизация app/parser/main.py
    main_py_path = 'app/parser/main.py'
    print(f"Применение оптимизаций к {main_py_path}...")
    
    with open(main_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Замена time.sleep(5) на time.sleep(2) (внутри запроса)
    content = re.sub(
        r'time\.sleep\(5\)\s*#.*?ускорения',
        'time.sleep(2)  # Уменьшено с 5 до 2 секунд для ускорения',
        content
    )
    content = re.sub(
        r'time\.sleep\(5\)\s*$',
        'time.sleep(2)  # Уменьшено с 5 до 2 секунд для ускорения',
        content,
        flags=re.MULTILINE
    )
    
    # Замена 45 секунд на 20 секунд после успешного запроса
    content = re.sub(
        r'proxyDict\[proxy\] = time\.time\(\) \+ 45\s*$',
        'proxyDict[proxy] = time.time() + 20  # Оптимизировано с 45 до 20 секунд',
        content,
        flags=re.MULTILINE
    )
    content = re.sub(
        r'proxyDict\[proxy\] = time\.time\(\) \+ 45\b',
        'proxyDict[proxy] = time.time() + 20',
        content
    )
    
    # Оптимизация логики ожидания прокси
    content = re.sub(
        r'if len\(available_proxies\) < 2:',
        'if len(available_proxies) < 1:  # Уменьшено с 2 до 1 для ускорения',
        content
    )
    content = re.sub(
        r'count = min\(len\(proxyDict\) - 1, 2\)',
        'count = min(len(proxyDict) - 1, 1)',
        content
    )
    # Добавляем ограничение 60 секунд для misstime
    if 'misstime = min(mintime - timenow, 60)' not in content:
        content = re.sub(
            r'misstime = mintime - timenow',
            'misstime = min(mintime - timenow, 60)  # Максимум 60 секунд ожидания',
            content
        )
    
    with open(main_py_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ {main_py_path} оптимизирован")
    
    # 2. Оптимизация app/scheduler/crontab.py
    crontab_py_path = 'app/scheduler/crontab.py'
    print(f"Применение оптимизаций к {crontab_py_path}...")
    
    with open(crontab_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Замена интервала с 3600 на 1800
    content = re.sub(
        r'PARSE_INTERVAL = 3600\s*#.*?минут',
        'PARSE_INTERVAL = 1800  # 30 минут между полными циклами (уменьшено с 60 до 30 минут для ускорения)',
        content
    )
    content = re.sub(
        r'PARSE_INTERVAL = 3600\b',
        'PARSE_INTERVAL = 1800  # 30 минут (уменьшено с 60 для ускорения)',
        content
    )
    
    with open(crontab_py_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ {crontab_py_path} оптимизирован")
    print("\n=== Все оптимизации применены ===")

if __name__ == '__main__':
    try:
        apply_optimizations()
        sys.exit(0)
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)

