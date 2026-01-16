#!/usr/bin/env python3
"""
Диагностический скрипт для проверки работы парсера.
Проверяет:
1. Работают ли прокси
2. Может ли парсер получить список объявлений
3. Может ли парсер получить страницу объявления
4. Есть ли новые объявления на CIAN
"""

import sys
import logging
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from app.parser.main import listPages, apartPage, getResponse
from app.parser.tools import proxyDict, check_and_unfreeze_proxies
from app.parser.database import DB, model_classes

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def check_proxies():
    """Проверяет состояние прокси"""
    print("\n=== Проверка прокси ===")
    check_and_unfreeze_proxies()
    non_empty_proxies = {k: v for k, v in proxyDict.items() if k != ''}
    print(f"Всего прокси: {len(non_empty_proxies)}")
    
    import time
    current_time = time.time()
    available = sum(1 for v in non_empty_proxies.values() if v <= current_time)
    blocked = len(non_empty_proxies) - available
    
    print(f"Доступных: {available}")
    print(f"Заблокированных: {blocked}")
    
    if blocked > 0:
        print("\nЗаблокированные прокси:")
        for proxy, block_until in non_empty_proxies.items():
            if block_until > current_time:
                block_duration = (block_until - current_time) / 60
                print(f"  {proxy[:50]}... - заблокирован на {block_duration:.1f} минут")

def check_list_pages():
    """Проверяет получение списка объявлений"""
    print("\n=== Проверка получения списка объявлений ===")
    
    # Пробуем несколько страниц
    test_pages = [1, 10, 50, 100]
    
    for page in test_pages:
        print(f"\nПроверка страницы {page}...")
        try:
            pglist = listPages(page, sort=None, rooms=None)
            
            if pglist == 'END':
                print(f"  Страница {page}: END (страница не существует)")
            elif pglist is None:
                print(f"  Страница {page}: None (ошибка получения)")
            elif isinstance(pglist, list):
                if len(pglist) == 0:
                    print(f"  Страница {page}: Пустой список (возможно CAPTCHA)")
                else:
                    print(f"  Страница {page}: Успех! Найдено {len(pglist)} объявлений")
                    print(f"  Первые 5 ID: {pglist[:5]}")
                    return pglist[:5]  # Возвращаем первые 5 для дальнейшей проверки
        except Exception as e:
            print(f"  Страница {page}: Ошибка - {e}")
    
    return None

def check_apart_page(cian_id):
    """Проверяет получение страницы объявления"""
    print(f"\n=== Проверка получения объявления {cian_id} ===")
    
    try:
        # Проверяем, есть ли уже в базе
        existing = DB.select(model_classes['offers'], filter_by={'cian_id': cian_id})
        if existing:
            print(f"  Объявление {cian_id} уже есть в базе")
            return 'EXISTING'
        
        # Пробуем получить страницу
        response = getResponse(cian_id, type=1, respTry=2)
        
        if response == 'CAPTCHA':
            print(f"  Объявление {cian_id}: CAPTCHA")
            return 'CAPTCHA'
        elif not response:
            print(f"  Объявление {cian_id}: Не удалось получить (None)")
            return None
        else:
            print(f"  Объявление {cian_id}: Успешно получено (длина: {len(response)} символов)")
            return response
    except Exception as e:
        print(f"  Объявление {cian_id}: Ошибка - {e}")
        return None

def check_parse_offer(cian_id):
    """Проверяет парсинг объявления"""
    print(f"\n=== Проверка парсинга объявления {cian_id} ===")
    
    try:
        # Пробуем распарсить
        result = apartPage([cian_id], dbinsert=False)  # Не вставляем в БД для теста
        
        if result == 'OK':
            print(f"  Объявление {cian_id}: Успешно распарсено")
            return True
        elif result == 'EXISTING':
            print(f"  Объявление {cian_id}: Уже в базе")
            return True
        elif result == 'FILTERED':
            print(f"  Объявление {cian_id}: Отфильтровано (не rent или dailyFlatRent)")
            return False
        elif result == 'SKIPPED':
            print(f"  Объявление {cian_id}: Пропущено (ошибка/CAPTCHA)")
            return False
        else:
            print(f"  Объявление {cian_id}: Неизвестный результат - {result}")
            return False
    except Exception as e:
        print(f"  Объявление {cian_id}: Ошибка парсинга - {e}")
        return False

def check_database():
    """Проверяет состояние базы данных"""
    print("\n=== Проверка базы данных ===")
    
    try:
        # Получаем количество объявлений
        offers = DB.select(model_classes['offers'])
        total_count = len(offers) if offers else 0
        print(f"Всего объявлений в базе: {total_count}")
        
        if total_count > 0:
            # Получаем последние 5 объявлений
            from app.parser.database import Offers
            session = DB.Session()
            try:
                last_offers = session.query(Offers).order_by(Offers.id.desc()).limit(5).all()
                print("\nПоследние 5 объявлений:")
                for offer in last_offers:
                    print(f"  ID: {offer.id}, CIAN ID: {offer.cian_id}, Цена: {offer.price}, Дата: {offer.publication_at}")
            finally:
                session.close()
    except Exception as e:
        print(f"Ошибка при проверке базы данных: {e}")

def main():
    print("=" * 60)
    print("ДИАГНОСТИКА ПАРСЕРА")
    print("=" * 60)
    
    # 1. Проверка прокси
    check_proxies()
    
    # 2. Проверка базы данных
    check_database()
    
    # 3. Проверка получения списка объявлений
    test_ids = check_list_pages()
    
    # 4. Если получили ID объявлений, проверяем их парсинг
    if test_ids:
        print("\n=== Проверка парсинга объявлений ===")
        for cian_id in test_ids[:3]:  # Проверяем первые 3
            check_apart_page(cian_id)
            check_parse_offer(cian_id)
    
    print("\n" + "=" * 60)
    print("ДИАГНОСТИКА ЗАВЕРШЕНА")
    print("=" * 60)

if __name__ == "__main__":
    main()

