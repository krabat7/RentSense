#!/usr/bin/env python3
"""
Скрипт для управления временной блокировкой/разблокировкой прокси.
Позволяет временно заблокировать старые прокси и использовать только новые,
а затем разблокировать все прокси для "ресета".
"""
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.parser.tools import proxyDict, proxyTemporaryBan, proxyBlockedTime, proxyErrorCount, proxyConnectionErrors, ban_proxies_by_pattern, unban_all_proxies, save_proxy_bans
import time

def list_proxies():
    """Показывает все прокси и их статус."""
    print("=" * 80)
    print("ТЕКУЩИЙ СТАТУС ПРОКСИ")
    print("=" * 80)
    print()
    
    current_time = time.time()
    total = len([p for p in proxyDict.keys() if p != ''])
    temporarily_banned = sum(1 for p in proxyDict.keys() if proxyTemporaryBan.get(p, False) and p != '')
    time_blocked = sum(1 for k, v in proxyDict.items() if v > current_time and k != '' and not proxyTemporaryBan.get(k, False))
    available = total - temporarily_banned - time_blocked
    
    print(f"Всего прокси: {total}")
    print(f"Временно забанено (proxyTemporaryBan): {temporarily_banned}")
    print(f"Заблокировано по времени (CAPTCHA/403): {time_blocked}")
    print(f"Доступно: {available}")
    print()
    
    print("Детали:")
    for i, proxy in enumerate([p for p in proxyDict.keys() if p != ''], 1):
        status = []
        if proxyTemporaryBan.get(proxy, False):
            status.append("[TEMPORARY_BAN]")
        if proxyDict[proxy] > current_time:
            blocked_until = proxyDict[proxy]
            block_duration = (blocked_until - current_time) / 60
            status.append(f"[BLOCKED {block_duration:.1f}min]")
        if proxyErrorCount.get(proxy, 0) > 0:
            status.append(f"[ERRORS: {proxyErrorCount[proxy]}]")
        if proxyConnectionErrors.get(proxy, 0) > 0:
            status.append(f"[CONN_ERR: {proxyConnectionErrors[proxy]}]")
        
        status_str = " ".join(status) if status else "[AVAILABLE]"
        print(f"  {i}. {proxy[:60]}... {status_str}")
    print()

def ban_old_proxies(exclude_patterns=None):
    """
    Блокирует все старые прокси, оставляя только новые.
    exclude_patterns - список паттернов для исключения (новые прокси).
    Например: exclude_patterns=['194.67', '23.229'] - будут использоваться только прокси с этими IP.
    """
    print("=" * 80)
    print("ВРЕМЕННАЯ БЛОКИРОВКА СТАРЫХ ПРОКСИ")
    print("=" * 80)
    print()
    
    if exclude_patterns:
        print(f"Исключаем прокси с паттернами: {exclude_patterns}")
        print("Будет заблокировано ВСЕ остальное.")
    else:
        print("ВНИМАНИЕ: Не указаны паттерны для исключения!")
        print("Все прокси будут заблокированы!")
        response = input("Продолжить? (yes/no): ")
        if response.lower() != 'yes':
            print("Отменено.")
            return
    
    # Блокируем все прокси (пустая строка как паттерн означает "все")
    banned = 0
    for proxy in proxyDict.keys():
        if proxy == '':
            continue
        
        # Если есть исключения, проверяем их
        if exclude_patterns:
            should_exclude = any(exc in proxy for exc in exclude_patterns)
            if should_exclude:
                print(f"  [SKIP] {proxy[:60]}... (matches exclude pattern)")
                continue
        
        # Блокируем прокси
        proxyTemporaryBan[proxy] = True
        banned += 1
        print(f"  [BANNED] {proxy[:60]}...")
    
    # Сохраняем баны в файл (чтобы парсер их увидел)
    save_proxy_bans(proxyTemporaryBan)
    print()
    print(f"Заблокировано {banned} прокси.")
    print(f"Баны сохранены в файл .proxy_bans")
    print()
    list_proxies()

def reset_all_proxies():
    """Разбан всех прокси и сброс всех счетчиков ошибок."""
    print("=" * 80)
    print("СБРОС ВСЕХ ПРОКСИ (РАЗБАН И ОЧИСТКА СЧЕТЧИКОВ)")
    print("=" * 80)
    print()
    
    response = input("Вы уверены, что хотите разбанить ВСЕ прокси и сбросить счетчики? (yes/no): ")
    if response.lower() != 'yes':
        print("Отменено.")
        return
    
    unbanned = unban_all_proxies()
    print()
    print(f"Разбанено {unbanned} прокси. Все счетчики сброшены.")
    print()
    list_proxies()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python manage_proxies.py list                    - Показать статус всех прокси")
        print("  python manage_proxies.py ban <pattern1> <pattern2> ... - Заблокировать прокси (кроме тех, что содержат pattern)")
        print("  python manage_proxies.py ban-all                 - Заблокировать ВСЕ прокси (опасно!)")
        print("  python manage_proxies.py reset                   - Разбанить ВСЕ прокси и сбросить счетчики")
        print()
        print("Примеры:")
        print("  python manage_proxies.py ban 194.67 23.229       - Заблокировать все, кроме прокси с IP 194.67.* и 23.229.*")
        print("  python manage_proxies.py ban new_proxy_prefix    - Заблокировать все, кроме прокси с 'new_proxy_prefix' в имени")
        print()
        list_proxies()
    elif sys.argv[1] == "list":
        list_proxies()
    elif sys.argv[1] == "ban":
        if len(sys.argv) < 3:
            print("Ошибка: Укажите паттерны для исключения (новые прокси).")
            print("Пример: python manage_proxies.py ban 194.67 23.229")
            sys.exit(1)
        exclude_patterns = sys.argv[2:]
        ban_old_proxies(exclude_patterns)
    elif sys.argv[1] == "ban-all":
        ban_old_proxies(exclude_patterns=None)
    elif sys.argv[1] == "reset":
        reset_all_proxies()
    else:
        print(f"Неизвестная команда: {sys.argv[1]}")
        sys.exit(1)

