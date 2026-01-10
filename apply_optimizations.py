#!/usr/bin/env python3
import re

# 1. Оптимизация app/parser/main.py
with open('app/parser/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Замена time.sleep(5) на time.sleep(2)
content = content.replace('time.sleep(5)', 'time.sleep(2)  # Уменьшено с 5 до 2 секунд для ускорения')

# Замена 45 секунд на 20 секунд
content = content.replace('time.time() + 45', 'time.time() + 20  # Оптимизировано с 45 до 20 секунд')

# Оптимизация логики ожидания прокси
content = content.replace('if len(available_proxies) < 2:', 'if len(available_proxies) < 1:  # Уменьшено с 2 до 1')
content = content.replace('count = min(len(proxyDict) - 1, 2)', 'count = min(len(proxyDict) - 1, 1)')
if 'misstime = min(mintime - timenow, 60)' not in content:
    content = content.replace('misstime = mintime - timenow', 'misstime = min(mintime - timenow, 60)  # Максимум 60 секунд')

with open('app/parser/main.py', 'w', encoding='utf-8') as f:
    f.write(content)
with open('app/scheduler/crontab.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('PARSE_INTERVAL = 3600', 'PARSE_INTERVAL = 1800  # 30 минут (уменьшено с 60)')

with open('app/scheduler/crontab.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Оптимизации применены")
