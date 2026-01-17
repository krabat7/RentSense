#!/usr/bin/env python3
"""
Комплексная диагностика парсера - проверяет все возможные проблемы
"""
import sys
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 80)
print("КОМПЛЕКСНАЯ ДИАГНОСТИКА ПАРСЕРА")
print("=" * 80)
print()

# ==========================================
# 1. ПРОВЕРКА: Парсер запущен?
# ==========================================
print("[1] Проверка статуса парсера...")
try:
    import subprocess
    result = subprocess.run(
        ['docker', 'ps', '--filter', 'name=parser', '--format', '{{.Status}}'],
        capture_output=True,
        text=True,
        timeout=5
    )
    if result.returncode == 0 and result.stdout.strip():
        print(f"   [OK] Парсер запущен: {result.stdout.strip()}")
    else:
        print("   [ERROR] Парсер НЕ запущен!")
        print("   Действие: Запустите парсер: docker-compose -f docker-compose.prod.yml up -d parser")
except Exception as e:
    print(f"   [WARN] Не удалось проверить статус: {e}")
print()

# ==========================================
# 2. ПРОВЕРКА: Последние логи парсера
# ==========================================
print("[2] Анализ последних логов парсера...")
try:
    result = subprocess.run(
        ['docker', 'logs', '--tail', '200', 'rentsense_parser_1'],
        capture_output=True,
        text=True,
        timeout=10
    )
    if result.returncode == 0:
        logs = result.stdout
        lines = logs.split('\n')
        
        # Проверяем наличие ошибок
        errors = [l for l in lines if 'ERROR' in l or 'Exception' in l or 'Traceback' in l]
        if errors:
            print(f"   [ERROR] Найдено {len(errors)} ошибок в логах:")
            for err in errors[-5:]:  # Последние 5 ошибок
                print(f"      {err[:150]}")
        else:
            print("   [OK] Ошибок в последних логах не найдено")
        
        # Проверяем последние действия
        last_actions = [l for l in lines if any(keyword in l for keyword in [
            'getResponse', 'listPages', 'apartPage', 'Starting parsing', 'SUCCESS', 
            'New offers added', 'CAPTCHA', 'blocked', 'connection error'
        ])][-10:]
        
        if last_actions:
            print(f"\n   Последние действия ({len(last_actions)} строк):")
            for action in last_actions:
                print(f"      {action[:150]}")
        else:
            print("   [WARN] В логах нет записей о действиях парсера (возможно, парсер завис)")
    else:
        print(f"   [ERROR] Не удалось получить логи: {result.stderr}")
except Exception as e:
    print(f"   [WARN] Не удалось проанализировать логи: {e}")
print()

# ==========================================
# 3. ПРОВЕРКА: Статус прокси
# ==========================================
print("[3] Проверка статуса прокси...")
try:
    from app.parser.tools import proxyDict, proxyBlockedTime, proxyErrorCount, proxyConnectionErrors
    import time as time_module
    
    current_time = time_module.time()
    total_proxies = len([p for p in proxyDict.keys() if p != ''])
    available_proxies = {k: v for k, v in proxyDict.items() if v <= current_time and k != ''}
    blocked_proxies = {k: v for k, v in proxyDict.items() if v > current_time and k != ''}
    
    print(f"   Всего прокси: {total_proxies}")
    print(f"   Доступно: {len(available_proxies)}")
    print(f"   Заблокировано: {len(blocked_proxies)}")
    
    if blocked_proxies:
        print(f"\n   Детали заблокированных прокси:")
        for proxy, block_until in list(blocked_proxies.items())[:5]:
            block_duration = (block_until - current_time) / 60
            error_count = proxyErrorCount.get(proxy, 0)
            conn_errors = proxyConnectionErrors.get(proxy, 0)
            print(f"      {proxy[:50]}... - заблокирован на {block_duration:.1f} мин (ошибок: {error_count}, подключений: {conn_errors})")
    
    if len(available_proxies) == 0:
        print("   [CRITICAL] Нет доступных прокси!")
        if blocked_proxies:
            min_unlock = min(v for v in blocked_proxies.values())
            unlock_time = (min_unlock - current_time) / 60
            print(f"   Самый ранний разблокируется через: {unlock_time:.1f} минут")
    elif len(available_proxies) < total_proxies * 0.3:
        print(f"   [WARN] Меньше 30% прокси доступно ({len(available_proxies)}/{total_proxies})")
    else:
        print(f"   [OK] Достаточно прокси доступно ({len(available_proxies)}/{total_proxies})")
except Exception as e:
    print(f"   [ERROR] Ошибка при проверке прокси: {e}")
    import traceback
    traceback.print_exc()
print()

# ==========================================
# 4. ПРОВЕРКА: База данных
# ==========================================
print("[4] Проверка базы данных...")
try:
    from app.parser.database import DB, Offers
    from sqlalchemy import func, desc
    
    session = DB.Session()
    try:
        # Общее количество объявлений
        total_count = session.query(func.count(Offers.cian_id)).scalar()
        print(f"   Всего объявлений в БД: {total_count}")
        
        # Последние добавленные объявления
        last_offers = session.query(Offers).order_by(desc(Offers.cian_id)).limit(5).all()
        if last_offers:
            print(f"\n   Последние 5 объявлений:")
            for offer in last_offers:
                print(f"      ID: {offer.cian_id}, Цена: {offer.price}, Дата: {offer.created_at}")
        
        # Объявления, добавленные за последние 4 часа
        four_hours_ago = datetime.now() - timedelta(hours=4)
        recent_count = session.query(func.count(Offers.cian_id)).filter(
            Offers.created_at >= four_hours_ago
        ).scalar()
        
        print(f"\n   Добавлено за последние 4 часа: {recent_count}")
        if recent_count == 0:
            print("   [CRITICAL] За последние 4 часа НЕ добавлено ни одного объявления!")
        else:
            print(f"   [OK] За последние 4 часа добавлено {recent_count} объявлений")
    finally:
        session.close()
except Exception as e:
    print(f"   [ERROR] Ошибка при проверке БД: {e}")
    import traceback
    traceback.print_exc()
print()

# ==========================================
# 5. ПРОВЕРКА: Тестовый запрос
# ==========================================
print("[5] Тестовый запрос к CIAN...")
try:
    from app.parser.main import listPages
    
    print("   Пытаюсь получить страницу 50...")
    result = listPages(50, sort=None, rooms=None)
    
    if isinstance(result, list) and len(result) > 0:
        print(f"   [OK] Успешно получено {len(result)} объявлений со страницы 50")
        print(f"   Первые 3 ID: {result[:3]}")
    elif result == 'END':
        print("   [WARN] Страница 50 вернула 'END' (конец списка)")
    elif isinstance(result, list) and len(result) == 0:
        print("   [WARN] Страница 50 вернула пустой список (возможно, CAPTCHA или ошибка)")
    elif result is None:
        print("   [ERROR] Страница 50 вернула None (критическая ошибка)")
    else:
        print(f"   [WARN] Неожиданный результат: {result}")
except Exception as e:
    print(f"   [ERROR] Ошибка при тестовом запросе: {e}")
    import traceback
    traceback.print_exc()
print()

# ==========================================
# 6. ПРОВЕРКА: find_start_page
# ==========================================
print("[6] Проверка функции find_start_page...")
try:
    from app.scheduler.tasks import parsing
    import asyncio
    
    # Импортируем функцию из локального контекста
    async def test_find_start_page():
        from app.parser.main import listPages
        import random
        
        test_pages = [300, 200, 150, 100, 50]
        max_quick_attempts = 3
        
        print(f"   Тестирую поиск стартовой страницы (проверю {max_quick_attempts} страницы)...")
        for i, test_page in enumerate(test_pages[:max_quick_attempts]):
            print(f"      Проверяю страницу {test_page}...")
            pglist = listPages(test_page, sort=None, rooms=None)
            
            if isinstance(pglist, list) and len(pglist) > 0:
                print(f"      [OK] Найдена валидная страница {test_page} с {len(pglist)} объявлениями")
                return test_page
            elif pglist == 'END':
                print(f"      [INFO] Страница {test_page} вернула 'END'")
            elif isinstance(pglist, list) and len(pglist) == 0:
                print(f"      [INFO] Страница {test_page} вернула пустой список")
            elif pglist is None:
                print(f"      [ERROR] Страница {test_page} вернула None (ошибка)")
            else:
                print(f"      [WARN] Страница {test_page} вернула неожиданный результат: {pglist}")
        
        fallback = random.randint(50, 250)
        print(f"   Использую случайную страницу {fallback} как fallback")
        return fallback
    
    result = asyncio.run(test_find_start_page())
    print(f"   [OK] find_start_page вернула страницу: {result}")
except Exception as e:
    print(f"   [ERROR] Ошибка при проверке find_start_page: {e}")
    import traceback
    traceback.print_exc()
print()

# ==========================================
# 7. ПРОВЕРКА: apartPage на реальном объявлении
# ==========================================
print("[7] Тестирование apartPage на реальном объявлении...")
try:
    from app.parser.main import listPages, apartPage
    
    print("   Получаю список объявлений со страницы 50...")
    pages_list = listPages(50, sort=None, rooms=None)
    
    if isinstance(pages_list, list) and len(pages_list) > 0:
        test_id = pages_list[0]
        print(f"   Тестирую парсинг объявления {test_id}...")
        result = apartPage([test_id], dbinsert=False)  # Без вставки в БД
        
        if isinstance(result, dict):
            print(f"   [OK] apartPage успешно распарсил объявление {test_id}")
            print(f"   Найдено данных: {list(result.keys())}")
        elif result == 'OK':
            print(f"   [OK] apartPage вернул 'OK' (объявление добавлено в БД)")
        elif result == 'EXISTING':
            print(f"   [WARN] apartPage вернул 'EXISTING' (объявление уже в БД)")
        elif result == 'FILTERED':
            print(f"   [WARN] apartPage вернул 'FILTERED' (объявление отфильтровано)")
        elif result == 'SKIPPED':
            print(f"   [ERROR] apartPage вернул 'SKIPPED' (объявление пропущено из-за ошибки)")
        elif result is None:
            print(f"   [ERROR] apartPage вернул None (критическая ошибка)")
        else:
            print(f"   [WARN] apartPage вернул неожиданный результат: {result}")
    else:
        print("   [WARN] Не удалось получить список объявлений для теста")
except Exception as e:
    print(f"   [ERROR] Ошибка при тестировании apartPage: {e}")
    import traceback
    traceback.print_exc()
print()

# ==========================================
# 8. ПРОВЕРКА: Анализ логов rentsense.log
# ==========================================
print("[8] Анализ логов rentsense.log...")
log_file = project_root / 'rentsense.log'
if log_file.exists():
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if lines:
            print(f"   Файл содержит {len(lines)} строк")
            
            # Последние 20 строк
            last_lines = lines[-20:]
            print(f"\n   Последние 20 строк:")
            for line in last_lines:
                print(f"      {line.rstrip()}")
            
            # Статистика по ключевым словам
            keywords = {
                'SUCCESS': 'Успешные добавления',
                'CAPTCHA': 'CAPTCHA обнаружены',
                'blocked': 'Блокировки прокси',
                'connection error': 'Ошибки подключения',
                'New offers added': 'Новые объявления',
            }
            
            print(f"\n   Статистика (последние 1000 строк):")
            recent_lines = lines[-1000:] if len(lines) > 1000 else lines
            for keyword, label in keywords.items():
                count = sum(1 for line in recent_lines if keyword in line)
                print(f"      {label}: {count}")
        else:
            print("   [WARN] Файл логов пуст")
    except Exception as e:
        print(f"   [ERROR] Ошибка при чтении логов: {e}")
else:
    print("   [WARN] Файл rentsense.log не найден")
print()

# ==========================================
# ИТОГОВЫЕ РЕКОМЕНДАЦИИ
# ==========================================
print("=" * 80)
print("ИТОГОВЫЕ РЕКОМЕНДАЦИИ:")
print("=" * 80)
print()
print("На основе диагностики, возможные проблемы:")
print()
print("1. Если парсер НЕ запущен:")
print("   => docker-compose -f docker-compose.prod.yml up -d parser")
print()
print("2. Если все прокси заблокированы:")
print("   => Подождите разблокировки или проверьте качество прокси")
print()
print("3. Если find_start_page не находит валидные страницы:")
print("   => Все прокси могут быть заблокированы или CIAN изменил структуру")
print()
print("4. Если apartPage возвращает 'SKIPPED' или 'FILTERED':")
print("   => Проверьте логи на наличие CAPTCHA и ошибок")
print()
print("5. Если нет новых объявлений в БД:")
print("   => Проверьте, что парсер действительно делает запросы (см. логи)")
print("   => Проверьте, не пропускаются ли все комбинации room/sort")
print("   => Проверьте, не застревает ли парсер на поиске стартовой страницы")
print()
print("=" * 80)

