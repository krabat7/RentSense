#!/usr/bin/env python3
"""
Скрипт для добавления новых прокси в .env файл.
Конвертирует формат host:port:username:password в http://username:password@host:port
"""
import sys
from pathlib import Path

# Новые прокси от пользователя (в формате host:port:username:password)
new_proxies = [
    "31.44.190.147:9657:4MfBTo:mgCBFh",
    "194.67.219.3:9623:4MfBTo:mgCBFh",
    "194.28.210.85:9963:4MfBTo:mgCBFh",
    "194.28.208.50:9743:4MfBTo:mgCBFh",
]

def convert_proxy_format(proxy_str):
    """Конвертирует host:port:username:password в http://username:password@host:port"""
    parts = proxy_str.split(':')
    if len(parts) != 4:
        raise ValueError(f"Неверный формат прокси: {proxy_str}. Ожидается host:port:username:password")
    host, port, username, password = parts
    return f"http://{username}:{password}@{host}:{port}"

def add_proxies_to_env():
    """Добавляет новые прокси в .env файл"""
    env_path = Path('.env')
    
    if not env_path.exists():
        print(f"[ERROR] Файл .env не найден в текущей директории: {Path.cwd()}")
        return False
    
    # Читаем текущий .env
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Находим максимальный номер PROXY
    max_proxy_num = 0
    for line in lines:
        if line.strip().startswith('PROXY'):
            try:
                # Извлекаем номер из PROXY1, PROXY2, etc.
                parts = line.split('=')[0].strip()
                num_str = parts.replace('PROXY', '')
                if num_str.isdigit():
                    max_proxy_num = max(max_proxy_num, int(num_str))
            except:
                pass
    
    # Конвертируем прокси и добавляем в .env
    converted_proxies = []
    for proxy_str in new_proxies:
        try:
            converted = convert_proxy_format(proxy_str)
            converted_proxies.append(converted)
            print(f"[OK] Конвертировано: {proxy_str[:30]}... -> {converted[:50]}...")
        except Exception as e:
            print(f"[ERROR] Ошибка при конвертации {proxy_str}: {e}")
            return False
    
    # Добавляем новые прокси
    proxy_added = False
    for i, proxy in enumerate(converted_proxies, 1):
        proxy_num = max_proxy_num + i
        new_line = f"PROXY{proxy_num}={proxy}\n"
        
        # Проверяем, нет ли уже такого прокси
        proxy_exists = any(proxy in line for line in lines)
        if proxy_exists:
            print(f"[SKIP] Прокси уже существует: PROXY{proxy_num}")
            continue
        
        lines.append(new_line)
        print(f"[OK] Добавлено: PROXY{proxy_num}={proxy[:50]}...")
        proxy_added = True
    
    if proxy_added:
        # Записываем обновленный .env
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"\n[OK] Всего добавлено {len([p for p in converted_proxies if p])} новых прокси в .env")
        return True
    else:
        print("\n[WARN] Новые прокси не были добавлены (возможно, уже существуют)")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("ДОБАВЛЕНИЕ НОВЫХ ПРОКСИ В .ENV")
    print("=" * 80)
    print()
    
    success = add_proxies_to_env()
    
    if success:
        print()
        print("=" * 80)
        print("СЛЕДУЮЩИЕ ШАГИ:")
        print("=" * 80)
        print("1. Перезапустите парсер: docker-compose -f docker-compose.prod.yml restart parser")
        print("2. Временно забаните старые прокси (оставив только новые):")
        print("   python manage_proxies.py ban 31.44 194.67.219 194.28.210 194.28.208")
        print("3. Через несколько часов разбаньте все:")
        print("   python manage_proxies.py reset")
        print()
    else:
        sys.exit(1)

