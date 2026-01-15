#!/usr/bin/env python3
"""
Скрипт для добавления новых прокси в .env файл.
Преобразует формат host:port:username:password в http://username:password@host:port
"""

import os
from pathlib import Path

# Новые прокси в формате host:port:username:password
new_proxies = [
    "213.139.222.69:9010:4D7D7f:mE9cRE",
    "213.139.222.149:9516:4D7D7f:mE9cRE",
    "213.139.223.145:9193:4D7D7f:mE9cRE",
    "213.139.222.227:9625:4D7D7f:mE9cRE",
    "212.102.145.24:9687:HrkB8A:GoTkpe",
    "212.102.144.77:9656:HrkB8A:GoTkpe",
    "178.171.43.146:9912:HrkB8A:GoTkpe",
    "194.67.219.124:9425:okJ0KF:9LmuSc",
    "194.67.222.245:9817:okJ0KF:9LmuSc",
    "194.67.223.76:9814:okJ0KF:9LmuSc",
    "194.67.219.15:9043:okJ0KF:9LmuSc",
]

def convert_proxy_format(proxy_str):
    """Преобразует host:port:username:password в http://username:password@host:port"""
    parts = proxy_str.split(':')
    if len(parts) != 4:
        raise ValueError(f"Неверный формат прокси: {proxy_str}")
    host, port, username, password = parts
    return f"http://{username}:{password}@{host}:{port}"

def read_env_file():
    """Читает существующий .env файл"""
    env_path = Path('.env')
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            return f.read().splitlines()
    return []

def find_next_proxy_number(lines):
    """Находит следующий свободный номер для PROXY"""
    max_num = 0
    for line in lines:
        if line.strip().startswith('PROXY') and '=' in line:
            try:
                num = int(line.split('PROXY')[1].split('=')[0])
                max_num = max(max_num, num)
            except:
                pass
    return max_num + 1

def main():
    # Преобразуем прокси в нужный формат
    converted_proxies = []
    for proxy in new_proxies:
        try:
            converted = convert_proxy_format(proxy)
            converted_proxies.append(converted)
            print(f"[OK] {proxy} -> {converted}")
        except Exception as e:
            print(f"[ERROR] Ошибка при преобразовании {proxy}: {e}")
    
    if not converted_proxies:
        print("Нет валидных прокси для добавления")
        return
    
    # Читаем существующий .env
    env_lines = read_env_file()
    
    # Находим следующий номер
    next_num = find_next_proxy_number(env_lines)
    
    # Добавляем новые прокси
    new_lines = []
    for i, proxy in enumerate(converted_proxies):
        proxy_num = next_num + i
        new_lines.append(f"PROXY{proxy_num}={proxy}")
        print(f"Добавлено: PROXY{proxy_num}={proxy}")
    
    # Объединяем старые и новые строки
    all_lines = env_lines + [''] + ['# Новые прокси (добавлено автоматически)'] + new_lines
    
    # Записываем в .env
    env_path = Path('.env')
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_lines) + '\n')
    
    print(f"\n[OK] Добавлено {len(converted_proxies)} прокси в .env файл")
    print(f"[INFO] Прокси начинаются с PROXY{next_num}")
    print("\n[WARNING] Не забудьте перезапустить парсер после обновления .env:")
    print("   docker-compose -f docker-compose.prod.yml restart parser")

if __name__ == '__main__':
    main()

