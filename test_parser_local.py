#!/usr/bin/env python3
"""
Локальный тест парсера для проверки работы перед заливкой на сервер.
Тестирует каждый этап парсинга с подробным логированием.
"""

import logging
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

from app.parser.main import listPages, apartPage
from app.parser.tools import load_proxy_bans, proxyDict, proxyTemporaryBan, proxyConnectionErrors
from app.parser.database import DB

def test_list_pages(page=1, sort=None, rooms=None):
    """Тестирует получение списка объявлений с первой страницы."""
    print(f"\n{'='*80}")
    print(f"TEST 1: listPages(page={page}, sort={sort}, rooms={rooms})")
    print(f"{'='*80}")
    
    result = listPages(page, sort, rooms)
    
    if result == 'END':
        print("[FAILED] listPages returned 'END' - страница недоступна")
        return False
    elif result is None:
        print("[FAILED] listPages returned None - критическая ошибка")
        return False
    elif isinstance(result, list):
        if len(result) == 0:
            print(f"[WARNING] listPages returned empty list (0 объявлений)")
            return 'empty'
        else:
            print(f"[SUCCESS] listPages returned {len(result)} объявлений")
            print(f"   First 5 IDs: {result[:5]}")
            return result
    else:
        print(f"[FAILED] listPages returned unexpected type: {type(result)}")
        return False

def test_apart_page(page_ids, max_test=3):
    """Тестирует парсинг отдельных объявлений."""
    print(f"\n{'='*80}")
    print(f"TEST 2: apartPage(page_ids[:{max_test}])")
    print(f"{'='*80}")
    
    if not page_ids:
        print("[SKIPPED] Empty page_ids list")
        return None
    
    test_ids = page_ids[:max_test]
    print(f"Testing {len(test_ids)} offers: {test_ids}")
    
    result = apartPage(test_ids, dbinsert=True)
    
    if result == 'OK':
        print(f"[SUCCESS] apartPage returned 'OK' - объявления обработаны/добавлены")
        return 'OK'
    elif result == 'EXISTING':
        print(f"[INFO] apartPage returned 'EXISTING' - все объявления уже в БД")
        return 'EXISTING'
    elif result == 'FILTERED':
        print(f"[INFO] apartPage returned 'FILTERED' - все объявления отфильтрованы")
        return 'FILTERED'
    elif result == 'SKIPPED':
        print(f"[WARNING] apartPage returned 'SKIPPED' - все объявления пропущены (CAPTCHA/ошибки)")
        return 'SKIPPED'
    elif result is None:
        print(f"[FAILED] apartPage returned None - ошибка обработки")
        return None
    else:
        print(f"[UNKNOWN] apartPage returned unexpected value: {result}")
        return result

def check_proxy_status():
    """Проверяет статус прокси."""
    print(f"\n{'='*80}")
    print(f"PROXY STATUS")
    print(f"{'='*80}")
    
    load_proxy_bans()
    
    total_proxies = len([p for p in proxyDict.keys() if p != ''])
    banned_proxies = sum(1 for p in proxyDict.keys() if p != '' and proxyTemporaryBan.get(p, False))
    
    print(f"Total proxies: {total_proxies}")
    print(f"Temporarily banned: {banned_proxies}")
    print(f"Available: {total_proxies - banned_proxies}")
    
    # Показываем статистику ошибок для первых 10 прокси
    print(f"\nConnection errors (first 10 proxies):")
    for i, (proxy, errors) in enumerate(sorted(proxyConnectionErrors.items(), key=lambda x: x[1])[:10]):
        if proxy and proxy != '':
            short_proxy = proxy[:60] + '...' if len(proxy) > 60 else proxy
            print(f"  {i+1}. {short_proxy}: {errors} errors")

def check_database():
    """Проверяет подключение к БД и количество объявлений."""
    print(f"\n{'='*80}")
    print(f"DATABASE STATUS")
    print(f"{'='*80}")
    
    try:
        from app.parser.database import model_classes
        from sqlalchemy import func
        
        # Проверяем подключение
        session = DB.Session()
        try:
            # Подсчитываем количество объявлений
            count = session.query(func.count(model_classes['offers'].cian_id)).scalar()
            print(f"[OK] Database connection: OK")
            print(f"Total offers in database: {count}")
            
            # Проверяем последние добавленные объявления
            recent = session.query(model_classes['offers']).order_by(
                model_classes['offers'].cian_id.desc()
            ).limit(5).all()
            
            if recent:
                print(f"\nLast 5 offers (cian_id):")
                for offer in recent:
                    print(f"  - {offer.cian_id}")
            else:
                print("[WARNING] No offers in database")
        finally:
            session.close()
                
    except Exception as e:
        print(f"[ERROR] Database connection error: {e}")
        print(f"  Note: Database may not be running locally. This is OK for testing parser logic.")
        return False
    
    return True

def main():
    """Основная функция тестирования."""
    print(f"\n{'#'*80}")
    print(f"LOCAL PARSER TEST - Step by step verification")
    print(f"{'#'*80}\n")
    
    # Временно блокируем старые прокси для теста только новых
    print(f"\n{'='*80}")
    print(f"BLOCKING OLD PROXIES FOR TEST")
    print(f"{'='*80}")
    
    # Паттерны новых прокси (IP адреса)
    new_proxy_patterns = ['158.46.182', '91.233.20', '46.19.71', '147.45.86', '195.64.101']
    
    # Блокируем все старые прокси
    load_proxy_bans()
    banned_count = 0
    for proxy in proxyDict.keys():
        if proxy == '':
            continue
        # Если прокси НЕ содержит паттерн новых прокси - блокируем
        if not any(pattern in proxy for pattern in new_proxy_patterns):
            proxyTemporaryBan[proxy] = True
            banned_count += 1
        else:
            # Разблокируем новые прокси на случай если они были заблокированы
            proxyTemporaryBan[proxy] = False
    
    # Сохраняем временные баны (они не будут сохранены в файл, только в память)
    print(f"[INFO] Temporarily banned {banned_count} old proxies for testing")
    print(f"[INFO] Using only new proxies: {[p for p in proxyDict.keys() if any(pat in p for pat in new_proxy_patterns) and p != '']}")
    
    # Шаг 1: Проверка статуса
    check_proxy_status()
    check_database()
    
    # Шаг 2: Тест получения списка объявлений
    print(f"\n{'='*80}")
    print(f"STEP 1: Testing listPages() - получение списка объявлений")
    print(f"{'='*80}")
    
    page_ids = test_list_pages(page=1, sort=None, rooms=None)
    
    if not page_ids:
        print("\n[CRITICAL] Cannot get list of offers. Parser will not work.")
        print("   Possible reasons:")
        print("   1. All proxies are blocked (403/CAPTCHA)")
        print("   2. Network connection issues")
        print("   3. CIAN.ru is blocking all requests")
        return 1
    
    if page_ids == 'empty':
        print("\n[WARNING] Empty page list. Trying next page...")
        page_ids = test_list_pages(page=2, sort=None, rooms=None)
        if not page_ids or page_ids == 'empty':
            print("\n[CRITICAL] Cannot get non-empty list of offers.")
            return 1
    
    # Шаг 3: Тест парсинга объявлений
    print(f"\n{'='*80}")
    print(f"STEP 2: Testing apartPage() - парсинг отдельных объявлений")
    print(f"{'='*80}")
    
    apart_result = test_apart_page(page_ids, max_test=5)
    
    # Шаг 4: Итоговый отчет
    print(f"\n{'='*80}")
    print(f"TEST SUMMARY")
    print(f"{'='*80}")
    
    if page_ids and isinstance(page_ids, list) and len(page_ids) > 0:
        print(f"[OK] listPages: OK ({len(page_ids)} offers found)")
    else:
        print(f"[FAILED] listPages: FAILED")
    
    if apart_result == 'OK':
        print(f"[OK] apartPage: OK (new offers added)")
    elif apart_result == 'EXISTING':
        print(f"[INFO] apartPage: All offers already exist (parser works, but nothing new)")
    elif apart_result == 'FILTERED':
        print(f"[INFO] apartPage: All offers filtered out")
    elif apart_result == 'SKIPPED':
        print(f"[WARNING] apartPage: All offers skipped (CAPTCHA/errors)")
    else:
        print(f"[FAILED] apartPage: FAILED")
    
    # Рекомендации
    print(f"\n{'='*80}")
    print(f"RECOMMENDATIONS")
    print(f"{'='*80}")
    
    if not page_ids or (isinstance(page_ids, list) and len(page_ids) == 0):
        print("[DO NOT DEPLOY] listPages is not working")
        print("   - Check proxy status")
        print("   - Check network connectivity")
        print("   - All proxies may be blocked by CIAN")
    elif apart_result == 'SKIPPED':
        print("[RISKY] apartPage is skipping all offers due to CAPTCHA/errors")
        print("   - Consider waiting for proxy cooldown")
        print("   - Check if proxies are working")
    elif apart_result == 'OK':
        print("[SAFE TO DEPLOY] Parser is working correctly")
    elif apart_result == 'EXISTING':
        print("[SAFE TO DEPLOY] Parser works, but no new offers found")
        print("   - This is normal if all offers are already in database")
    else:
        print("[REVIEW NEEDED] Unexpected results, check logs")
    
    return 0 if (page_ids and apart_result in ['OK', 'EXISTING']) else 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)


Локальный тест парсера для проверки работы перед заливкой на сервер.
Тестирует каждый этап парсинга с подробным логированием.
"""

import logging
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

from app.parser.main import listPages, apartPage
from app.parser.tools import load_proxy_bans, proxyDict, proxyTemporaryBan, proxyConnectionErrors
from app.parser.database import DB

def test_list_pages(page=1, sort=None, rooms=None):
    """Тестирует получение списка объявлений с первой страницы."""
    print(f"\n{'='*80}")
    print(f"TEST 1: listPages(page={page}, sort={sort}, rooms={rooms})")
    print(f"{'='*80}")
    
    result = listPages(page, sort, rooms)
    
    if result == 'END':
        print("[FAILED] listPages returned 'END' - страница недоступна")
        return False
    elif result is None:
        print("[FAILED] listPages returned None - критическая ошибка")
        return False
    elif isinstance(result, list):
        if len(result) == 0:
            print(f"[WARNING] listPages returned empty list (0 объявлений)")
            return 'empty'
        else:
            print(f"[SUCCESS] listPages returned {len(result)} объявлений")
            print(f"   First 5 IDs: {result[:5]}")
            return result
    else:
        print(f"[FAILED] listPages returned unexpected type: {type(result)}")
        return False

def test_apart_page(page_ids, max_test=3):
    """Тестирует парсинг отдельных объявлений."""
    print(f"\n{'='*80}")
    print(f"TEST 2: apartPage(page_ids[:{max_test}])")
    print(f"{'='*80}")
    
    if not page_ids:
        print("[SKIPPED] Empty page_ids list")
        return None
    
    test_ids = page_ids[:max_test]
    print(f"Testing {len(test_ids)} offers: {test_ids}")
    
    result = apartPage(test_ids, dbinsert=True)
    
    if result == 'OK':
        print(f"[SUCCESS] apartPage returned 'OK' - объявления обработаны/добавлены")
        return 'OK'
    elif result == 'EXISTING':
        print(f"[INFO] apartPage returned 'EXISTING' - все объявления уже в БД")
        return 'EXISTING'
    elif result == 'FILTERED':
        print(f"[INFO] apartPage returned 'FILTERED' - все объявления отфильтрованы")
        return 'FILTERED'
    elif result == 'SKIPPED':
        print(f"[WARNING] apartPage returned 'SKIPPED' - все объявления пропущены (CAPTCHA/ошибки)")
        return 'SKIPPED'
    elif result is None:
        print(f"[FAILED] apartPage returned None - ошибка обработки")
        return None
    else:
        print(f"[UNKNOWN] apartPage returned unexpected value: {result}")
        return result

def check_proxy_status():
    """Проверяет статус прокси."""
    print(f"\n{'='*80}")
    print(f"PROXY STATUS")
    print(f"{'='*80}")
    
    load_proxy_bans()
    
    total_proxies = len([p for p in proxyDict.keys() if p != ''])
    banned_proxies = sum(1 for p in proxyDict.keys() if p != '' and proxyTemporaryBan.get(p, False))
    
    print(f"Total proxies: {total_proxies}")
    print(f"Temporarily banned: {banned_proxies}")
    print(f"Available: {total_proxies - banned_proxies}")
    
    # Показываем статистику ошибок для первых 10 прокси
    print(f"\nConnection errors (first 10 proxies):")
    for i, (proxy, errors) in enumerate(sorted(proxyConnectionErrors.items(), key=lambda x: x[1])[:10]):
        if proxy and proxy != '':
            short_proxy = proxy[:60] + '...' if len(proxy) > 60 else proxy
            print(f"  {i+1}. {short_proxy}: {errors} errors")

def check_database():
    """Проверяет подключение к БД и количество объявлений."""
    print(f"\n{'='*80}")
    print(f"DATABASE STATUS")
    print(f"{'='*80}")
    
    try:
        from app.parser.database import model_classes
        from sqlalchemy import func
        
        # Проверяем подключение
        session = DB.Session()
        try:
            # Подсчитываем количество объявлений
            count = session.query(func.count(model_classes['offers'].cian_id)).scalar()
            print(f"[OK] Database connection: OK")
            print(f"Total offers in database: {count}")
            
            # Проверяем последние добавленные объявления
            recent = session.query(model_classes['offers']).order_by(
                model_classes['offers'].cian_id.desc()
            ).limit(5).all()
            
            if recent:
                print(f"\nLast 5 offers (cian_id):")
                for offer in recent:
                    print(f"  - {offer.cian_id}")
            else:
                print("[WARNING] No offers in database")
        finally:
            session.close()
                
    except Exception as e:
        print(f"[ERROR] Database connection error: {e}")
        print(f"  Note: Database may not be running locally. This is OK for testing parser logic.")
        return False
    
    return True

def main():
    """Основная функция тестирования."""
    print(f"\n{'#'*80}")
    print(f"LOCAL PARSER TEST - Step by step verification")
    print(f"{'#'*80}\n")
    
    # Временно блокируем старые прокси для теста только новых
    print(f"\n{'='*80}")
    print(f"BLOCKING OLD PROXIES FOR TEST")
    print(f"{'='*80}")
    
    # Паттерны новых прокси (IP адреса)
    new_proxy_patterns = ['158.46.182', '91.233.20', '46.19.71', '147.45.86', '195.64.101']
    
    # Блокируем все старые прокси
    load_proxy_bans()
    banned_count = 0
    for proxy in proxyDict.keys():
        if proxy == '':
            continue
        # Если прокси НЕ содержит паттерн новых прокси - блокируем
        if not any(pattern in proxy for pattern in new_proxy_patterns):
            proxyTemporaryBan[proxy] = True
            banned_count += 1
        else:
            # Разблокируем новые прокси на случай если они были заблокированы
            proxyTemporaryBan[proxy] = False
    
    # Сохраняем временные баны (они не будут сохранены в файл, только в память)
    print(f"[INFO] Temporarily banned {banned_count} old proxies for testing")
    print(f"[INFO] Using only new proxies: {[p for p in proxyDict.keys() if any(pat in p for pat in new_proxy_patterns) and p != '']}")
    
    # Шаг 1: Проверка статуса
    check_proxy_status()
    check_database()
    
    # Шаг 2: Тест получения списка объявлений
    print(f"\n{'='*80}")
    print(f"STEP 1: Testing listPages() - получение списка объявлений")
    print(f"{'='*80}")
    
    page_ids = test_list_pages(page=1, sort=None, rooms=None)
    
    if not page_ids:
        print("\n[CRITICAL] Cannot get list of offers. Parser will not work.")
        print("   Possible reasons:")
        print("   1. All proxies are blocked (403/CAPTCHA)")
        print("   2. Network connection issues")
        print("   3. CIAN.ru is blocking all requests")
        return 1
    
    if page_ids == 'empty':
        print("\n[WARNING] Empty page list. Trying next page...")
        page_ids = test_list_pages(page=2, sort=None, rooms=None)
        if not page_ids or page_ids == 'empty':
            print("\n[CRITICAL] Cannot get non-empty list of offers.")
            return 1
    
    # Шаг 3: Тест парсинга объявлений
    print(f"\n{'='*80}")
    print(f"STEP 2: Testing apartPage() - парсинг отдельных объявлений")
    print(f"{'='*80}")
    
    apart_result = test_apart_page(page_ids, max_test=5)
    
    # Шаг 4: Итоговый отчет
    print(f"\n{'='*80}")
    print(f"TEST SUMMARY")
    print(f"{'='*80}")
    
    if page_ids and isinstance(page_ids, list) and len(page_ids) > 0:
        print(f"[OK] listPages: OK ({len(page_ids)} offers found)")
    else:
        print(f"[FAILED] listPages: FAILED")
    
    if apart_result == 'OK':
        print(f"[OK] apartPage: OK (new offers added)")
    elif apart_result == 'EXISTING':
        print(f"[INFO] apartPage: All offers already exist (parser works, but nothing new)")
    elif apart_result == 'FILTERED':
        print(f"[INFO] apartPage: All offers filtered out")
    elif apart_result == 'SKIPPED':
        print(f"[WARNING] apartPage: All offers skipped (CAPTCHA/errors)")
    else:
        print(f"[FAILED] apartPage: FAILED")
    
    # Рекомендации
    print(f"\n{'='*80}")
    print(f"RECOMMENDATIONS")
    print(f"{'='*80}")
    
    if not page_ids or (isinstance(page_ids, list) and len(page_ids) == 0):
        print("[DO NOT DEPLOY] listPages is not working")
        print("   - Check proxy status")
        print("   - Check network connectivity")
        print("   - All proxies may be blocked by CIAN")
    elif apart_result == 'SKIPPED':
        print("[RISKY] apartPage is skipping all offers due to CAPTCHA/errors")
        print("   - Consider waiting for proxy cooldown")
        print("   - Check if proxies are working")
    elif apart_result == 'OK':
        print("[SAFE TO DEPLOY] Parser is working correctly")
    elif apart_result == 'EXISTING':
        print("[SAFE TO DEPLOY] Parser works, but no new offers found")
        print("   - This is normal if all offers are already in database")
    else:
        print("[REVIEW NEEDED] Unexpected results, check logs")
    
    return 0 if (page_ids and apart_result in ['OK', 'EXISTING']) else 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)


Локальный тест парсера для проверки работы перед заливкой на сервер.
Тестирует каждый этап парсинга с подробным логированием.
"""

import logging
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

from app.parser.main import listPages, apartPage
from app.parser.tools import load_proxy_bans, proxyDict, proxyTemporaryBan, proxyConnectionErrors
from app.parser.database import DB

def test_list_pages(page=1, sort=None, rooms=None):
    """Тестирует получение списка объявлений с первой страницы."""
    print(f"\n{'='*80}")
    print(f"TEST 1: listPages(page={page}, sort={sort}, rooms={rooms})")
    print(f"{'='*80}")
    
    result = listPages(page, sort, rooms)
    
    if result == 'END':
        print("[FAILED] listPages returned 'END' - страница недоступна")
        return False
    elif result is None:
        print("[FAILED] listPages returned None - критическая ошибка")
        return False
    elif isinstance(result, list):
        if len(result) == 0:
            print(f"[WARNING] listPages returned empty list (0 объявлений)")
            return 'empty'
        else:
            print(f"[SUCCESS] listPages returned {len(result)} объявлений")
            print(f"   First 5 IDs: {result[:5]}")
            return result
    else:
        print(f"[FAILED] listPages returned unexpected type: {type(result)}")
        return False

def test_apart_page(page_ids, max_test=3):
    """Тестирует парсинг отдельных объявлений."""
    print(f"\n{'='*80}")
    print(f"TEST 2: apartPage(page_ids[:{max_test}])")
    print(f"{'='*80}")
    
    if not page_ids:
        print("[SKIPPED] Empty page_ids list")
        return None
    
    test_ids = page_ids[:max_test]
    print(f"Testing {len(test_ids)} offers: {test_ids}")
    
    result = apartPage(test_ids, dbinsert=True)
    
    if result == 'OK':
        print(f"[SUCCESS] apartPage returned 'OK' - объявления обработаны/добавлены")
        return 'OK'
    elif result == 'EXISTING':
        print(f"[INFO] apartPage returned 'EXISTING' - все объявления уже в БД")
        return 'EXISTING'
    elif result == 'FILTERED':
        print(f"[INFO] apartPage returned 'FILTERED' - все объявления отфильтрованы")
        return 'FILTERED'
    elif result == 'SKIPPED':
        print(f"[WARNING] apartPage returned 'SKIPPED' - все объявления пропущены (CAPTCHA/ошибки)")
        return 'SKIPPED'
    elif result is None:
        print(f"[FAILED] apartPage returned None - ошибка обработки")
        return None
    else:
        print(f"[UNKNOWN] apartPage returned unexpected value: {result}")
        return result

def check_proxy_status():
    """Проверяет статус прокси."""
    print(f"\n{'='*80}")
    print(f"PROXY STATUS")
    print(f"{'='*80}")
    
    load_proxy_bans()
    
    total_proxies = len([p for p in proxyDict.keys() if p != ''])
    banned_proxies = sum(1 for p in proxyDict.keys() if p != '' and proxyTemporaryBan.get(p, False))
    
    print(f"Total proxies: {total_proxies}")
    print(f"Temporarily banned: {banned_proxies}")
    print(f"Available: {total_proxies - banned_proxies}")
    
    # Показываем статистику ошибок для первых 10 прокси
    print(f"\nConnection errors (first 10 proxies):")
    for i, (proxy, errors) in enumerate(sorted(proxyConnectionErrors.items(), key=lambda x: x[1])[:10]):
        if proxy and proxy != '':
            short_proxy = proxy[:60] + '...' if len(proxy) > 60 else proxy
            print(f"  {i+1}. {short_proxy}: {errors} errors")

def check_database():
    """Проверяет подключение к БД и количество объявлений."""
    print(f"\n{'='*80}")
    print(f"DATABASE STATUS")
    print(f"{'='*80}")
    
    try:
        from app.parser.database import model_classes
        from sqlalchemy import func
        
        # Проверяем подключение
        session = DB.Session()
        try:
            # Подсчитываем количество объявлений
            count = session.query(func.count(model_classes['offers'].cian_id)).scalar()
            print(f"[OK] Database connection: OK")
            print(f"Total offers in database: {count}")
            
            # Проверяем последние добавленные объявления
            recent = session.query(model_classes['offers']).order_by(
                model_classes['offers'].cian_id.desc()
            ).limit(5).all()
            
            if recent:
                print(f"\nLast 5 offers (cian_id):")
                for offer in recent:
                    print(f"  - {offer.cian_id}")
            else:
                print("[WARNING] No offers in database")
        finally:
            session.close()
                
    except Exception as e:
        print(f"[ERROR] Database connection error: {e}")
        print(f"  Note: Database may not be running locally. This is OK for testing parser logic.")
        return False
    
    return True

def main():
    """Основная функция тестирования."""
    print(f"\n{'#'*80}")
    print(f"LOCAL PARSER TEST - Step by step verification")
    print(f"{'#'*80}\n")
    
    # Временно блокируем старые прокси для теста только новых
    print(f"\n{'='*80}")
    print(f"BLOCKING OLD PROXIES FOR TEST")
    print(f"{'='*80}")
    
    # Паттерны новых прокси (IP адреса)
    new_proxy_patterns = ['158.46.182', '91.233.20', '46.19.71', '147.45.86', '195.64.101']
    
    # Блокируем все старые прокси
    load_proxy_bans()
    banned_count = 0
    for proxy in proxyDict.keys():
        if proxy == '':
            continue
        # Если прокси НЕ содержит паттерн новых прокси - блокируем
        if not any(pattern in proxy for pattern in new_proxy_patterns):
            proxyTemporaryBan[proxy] = True
            banned_count += 1
        else:
            # Разблокируем новые прокси на случай если они были заблокированы
            proxyTemporaryBan[proxy] = False
    
    # Сохраняем временные баны (они не будут сохранены в файл, только в память)
    print(f"[INFO] Temporarily banned {banned_count} old proxies for testing")
    print(f"[INFO] Using only new proxies: {[p for p in proxyDict.keys() if any(pat in p for pat in new_proxy_patterns) and p != '']}")
    
    # Шаг 1: Проверка статуса
    check_proxy_status()
    check_database()
    
    # Шаг 2: Тест получения списка объявлений
    print(f"\n{'='*80}")
    print(f"STEP 1: Testing listPages() - получение списка объявлений")
    print(f"{'='*80}")
    
    page_ids = test_list_pages(page=1, sort=None, rooms=None)
    
    if not page_ids:
        print("\n[CRITICAL] Cannot get list of offers. Parser will not work.")
        print("   Possible reasons:")
        print("   1. All proxies are blocked (403/CAPTCHA)")
        print("   2. Network connection issues")
        print("   3. CIAN.ru is blocking all requests")
        return 1
    
    if page_ids == 'empty':
        print("\n[WARNING] Empty page list. Trying next page...")
        page_ids = test_list_pages(page=2, sort=None, rooms=None)
        if not page_ids or page_ids == 'empty':
            print("\n[CRITICAL] Cannot get non-empty list of offers.")
            return 1
    
    # Шаг 3: Тест парсинга объявлений
    print(f"\n{'='*80}")
    print(f"STEP 2: Testing apartPage() - парсинг отдельных объявлений")
    print(f"{'='*80}")
    
    apart_result = test_apart_page(page_ids, max_test=5)
    
    # Шаг 4: Итоговый отчет
    print(f"\n{'='*80}")
    print(f"TEST SUMMARY")
    print(f"{'='*80}")
    
    if page_ids and isinstance(page_ids, list) and len(page_ids) > 0:
        print(f"[OK] listPages: OK ({len(page_ids)} offers found)")
    else:
        print(f"[FAILED] listPages: FAILED")
    
    if apart_result == 'OK':
        print(f"[OK] apartPage: OK (new offers added)")
    elif apart_result == 'EXISTING':
        print(f"[INFO] apartPage: All offers already exist (parser works, but nothing new)")
    elif apart_result == 'FILTERED':
        print(f"[INFO] apartPage: All offers filtered out")
    elif apart_result == 'SKIPPED':
        print(f"[WARNING] apartPage: All offers skipped (CAPTCHA/errors)")
    else:
        print(f"[FAILED] apartPage: FAILED")
    
    # Рекомендации
    print(f"\n{'='*80}")
    print(f"RECOMMENDATIONS")
    print(f"{'='*80}")
    
    if not page_ids or (isinstance(page_ids, list) and len(page_ids) == 0):
        print("[DO NOT DEPLOY] listPages is not working")
        print("   - Check proxy status")
        print("   - Check network connectivity")
        print("   - All proxies may be blocked by CIAN")
    elif apart_result == 'SKIPPED':
        print("[RISKY] apartPage is skipping all offers due to CAPTCHA/errors")
        print("   - Consider waiting for proxy cooldown")
        print("   - Check if proxies are working")
    elif apart_result == 'OK':
        print("[SAFE TO DEPLOY] Parser is working correctly")
    elif apart_result == 'EXISTING':
        print("[SAFE TO DEPLOY] Parser works, but no new offers found")
        print("   - This is normal if all offers are already in database")
    else:
        print("[REVIEW NEEDED] Unexpected results, check logs")
    
    return 0 if (page_ids and apart_result in ['OK', 'EXISTING']) else 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)


Локальный тест парсера для проверки работы перед заливкой на сервер.
Тестирует каждый этап парсинга с подробным логированием.
"""

import logging
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

from app.parser.main import listPages, apartPage
from app.parser.tools import load_proxy_bans, proxyDict, proxyTemporaryBan, proxyConnectionErrors
from app.parser.database import DB

def test_list_pages(page=1, sort=None, rooms=None):
    """Тестирует получение списка объявлений с первой страницы."""
    print(f"\n{'='*80}")
    print(f"TEST 1: listPages(page={page}, sort={sort}, rooms={rooms})")
    print(f"{'='*80}")
    
    result = listPages(page, sort, rooms)
    
    if result == 'END':
        print("[FAILED] listPages returned 'END' - страница недоступна")
        return False
    elif result is None:
        print("[FAILED] listPages returned None - критическая ошибка")
        return False
    elif isinstance(result, list):
        if len(result) == 0:
            print(f"[WARNING] listPages returned empty list (0 объявлений)")
            return 'empty'
        else:
            print(f"[SUCCESS] listPages returned {len(result)} объявлений")
            print(f"   First 5 IDs: {result[:5]}")
            return result
    else:
        print(f"[FAILED] listPages returned unexpected type: {type(result)}")
        return False

def test_apart_page(page_ids, max_test=3):
    """Тестирует парсинг отдельных объявлений."""
    print(f"\n{'='*80}")
    print(f"TEST 2: apartPage(page_ids[:{max_test}])")
    print(f"{'='*80}")
    
    if not page_ids:
        print("[SKIPPED] Empty page_ids list")
        return None
    
    test_ids = page_ids[:max_test]
    print(f"Testing {len(test_ids)} offers: {test_ids}")
    
    result = apartPage(test_ids, dbinsert=True)
    
    if result == 'OK':
        print(f"[SUCCESS] apartPage returned 'OK' - объявления обработаны/добавлены")
        return 'OK'
    elif result == 'EXISTING':
        print(f"[INFO] apartPage returned 'EXISTING' - все объявления уже в БД")
        return 'EXISTING'
    elif result == 'FILTERED':
        print(f"[INFO] apartPage returned 'FILTERED' - все объявления отфильтрованы")
        return 'FILTERED'
    elif result == 'SKIPPED':
        print(f"[WARNING] apartPage returned 'SKIPPED' - все объявления пропущены (CAPTCHA/ошибки)")
        return 'SKIPPED'
    elif result is None:
        print(f"[FAILED] apartPage returned None - ошибка обработки")
        return None
    else:
        print(f"[UNKNOWN] apartPage returned unexpected value: {result}")
        return result

def check_proxy_status():
    """Проверяет статус прокси."""
    print(f"\n{'='*80}")
    print(f"PROXY STATUS")
    print(f"{'='*80}")
    
    load_proxy_bans()
    
    total_proxies = len([p for p in proxyDict.keys() if p != ''])
    banned_proxies = sum(1 for p in proxyDict.keys() if p != '' and proxyTemporaryBan.get(p, False))
    
    print(f"Total proxies: {total_proxies}")
    print(f"Temporarily banned: {banned_proxies}")
    print(f"Available: {total_proxies - banned_proxies}")
    
    # Показываем статистику ошибок для первых 10 прокси
    print(f"\nConnection errors (first 10 proxies):")
    for i, (proxy, errors) in enumerate(sorted(proxyConnectionErrors.items(), key=lambda x: x[1])[:10]):
        if proxy and proxy != '':
            short_proxy = proxy[:60] + '...' if len(proxy) > 60 else proxy
            print(f"  {i+1}. {short_proxy}: {errors} errors")

def check_database():
    """Проверяет подключение к БД и количество объявлений."""
    print(f"\n{'='*80}")
    print(f"DATABASE STATUS")
    print(f"{'='*80}")
    
    try:
        from app.parser.database import model_classes
        from sqlalchemy import func
        
        # Проверяем подключение
        session = DB.Session()
        try:
            # Подсчитываем количество объявлений
            count = session.query(func.count(model_classes['offers'].cian_id)).scalar()
            print(f"[OK] Database connection: OK")
            print(f"Total offers in database: {count}")
            
            # Проверяем последние добавленные объявления
            recent = session.query(model_classes['offers']).order_by(
                model_classes['offers'].cian_id.desc()
            ).limit(5).all()
            
            if recent:
                print(f"\nLast 5 offers (cian_id):")
                for offer in recent:
                    print(f"  - {offer.cian_id}")
            else:
                print("[WARNING] No offers in database")
        finally:
            session.close()
                
    except Exception as e:
        print(f"[ERROR] Database connection error: {e}")
        print(f"  Note: Database may not be running locally. This is OK for testing parser logic.")
        return False
    
    return True

def main():
    """Основная функция тестирования."""
    print(f"\n{'#'*80}")
    print(f"LOCAL PARSER TEST - Step by step verification")
    print(f"{'#'*80}\n")
    
    # Временно блокируем старые прокси для теста только новых
    print(f"\n{'='*80}")
    print(f"BLOCKING OLD PROXIES FOR TEST")
    print(f"{'='*80}")
    
    # Паттерны новых прокси (IP адреса)
    new_proxy_patterns = ['158.46.182', '91.233.20', '46.19.71', '147.45.86', '195.64.101']
    
    # Блокируем все старые прокси
    load_proxy_bans()
    banned_count = 0
    for proxy in proxyDict.keys():
        if proxy == '':
            continue
        # Если прокси НЕ содержит паттерн новых прокси - блокируем
        if not any(pattern in proxy for pattern in new_proxy_patterns):
            proxyTemporaryBan[proxy] = True
            banned_count += 1
        else:
            # Разблокируем новые прокси на случай если они были заблокированы
            proxyTemporaryBan[proxy] = False
    
    # Сохраняем временные баны (они не будут сохранены в файл, только в память)
    print(f"[INFO] Temporarily banned {banned_count} old proxies for testing")
    print(f"[INFO] Using only new proxies: {[p for p in proxyDict.keys() if any(pat in p for pat in new_proxy_patterns) and p != '']}")
    
    # Шаг 1: Проверка статуса
    check_proxy_status()
    check_database()
    
    # Шаг 2: Тест получения списка объявлений
    print(f"\n{'='*80}")
    print(f"STEP 1: Testing listPages() - получение списка объявлений")
    print(f"{'='*80}")
    
    page_ids = test_list_pages(page=1, sort=None, rooms=None)
    
    if not page_ids:
        print("\n[CRITICAL] Cannot get list of offers. Parser will not work.")
        print("   Possible reasons:")
        print("   1. All proxies are blocked (403/CAPTCHA)")
        print("   2. Network connection issues")
        print("   3. CIAN.ru is blocking all requests")
        return 1
    
    if page_ids == 'empty':
        print("\n[WARNING] Empty page list. Trying next page...")
        page_ids = test_list_pages(page=2, sort=None, rooms=None)
        if not page_ids or page_ids == 'empty':
            print("\n[CRITICAL] Cannot get non-empty list of offers.")
            return 1
    
    # Шаг 3: Тест парсинга объявлений
    print(f"\n{'='*80}")
    print(f"STEP 2: Testing apartPage() - парсинг отдельных объявлений")
    print(f"{'='*80}")
    
    apart_result = test_apart_page(page_ids, max_test=5)
    
    # Шаг 4: Итоговый отчет
    print(f"\n{'='*80}")
    print(f"TEST SUMMARY")
    print(f"{'='*80}")
    
    if page_ids and isinstance(page_ids, list) and len(page_ids) > 0:
        print(f"[OK] listPages: OK ({len(page_ids)} offers found)")
    else:
        print(f"[FAILED] listPages: FAILED")
    
    if apart_result == 'OK':
        print(f"[OK] apartPage: OK (new offers added)")
    elif apart_result == 'EXISTING':
        print(f"[INFO] apartPage: All offers already exist (parser works, but nothing new)")
    elif apart_result == 'FILTERED':
        print(f"[INFO] apartPage: All offers filtered out")
    elif apart_result == 'SKIPPED':
        print(f"[WARNING] apartPage: All offers skipped (CAPTCHA/errors)")
    else:
        print(f"[FAILED] apartPage: FAILED")
    
    # Рекомендации
    print(f"\n{'='*80}")
    print(f"RECOMMENDATIONS")
    print(f"{'='*80}")
    
    if not page_ids or (isinstance(page_ids, list) and len(page_ids) == 0):
        print("[DO NOT DEPLOY] listPages is not working")
        print("   - Check proxy status")
        print("   - Check network connectivity")
        print("   - All proxies may be blocked by CIAN")
    elif apart_result == 'SKIPPED':
        print("[RISKY] apartPage is skipping all offers due to CAPTCHA/errors")
        print("   - Consider waiting for proxy cooldown")
        print("   - Check if proxies are working")
    elif apart_result == 'OK':
        print("[SAFE TO DEPLOY] Parser is working correctly")
    elif apart_result == 'EXISTING':
        print("[SAFE TO DEPLOY] Parser works, but no new offers found")
        print("   - This is normal if all offers are already in database")
    else:
        print("[REVIEW NEEDED] Unexpected results, check logs")
    
    return 0 if (page_ids and apart_result in ['OK', 'EXISTING']) else 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

