#!/usr/bin/env python3
"""Исправление отступов в main.py на сервере"""

# Правильная версия функции apartPage
correct_apartPage = '''def apartPage(pagesList, dbinsert=True, max_retries=2):
    """
    Парсит список объявлений с улучшенной логикой пропуска проблемных.
    max_retries - максимальное количество попыток для одного объявления
    """
    pages_cnt = 0
    skipped_count = 0
    failed_pages = {}  # Счетчик неудачных попыток для каждого объявления
    
    for page in pagesList:
        exist = False
        if dbinsert and DB.select(model_classes['offers'], filter_by={'cian_id': page}):
            exist = True
            logging.info(f"Apart page {page} already exists")
            continue
        
        # Проверяем, сколько раз мы уже пытались парсить это объявление
        retry_count = failed_pages.get(page, 0)
        if retry_count >= max_retries:
            skipped_count += 1
            logging.info(f"Apart page {page} skipped after {retry_count} failed attempts")
            continue
        
        if not (response := getResponse(page, type=1, dbinsert=dbinsert, respTry=3)):  # Уменьшено с 5 до 3 попыток
            failed_pages[page] = retry_count + 1
            if retry_count + 1 < max_retries:
                logging.info(f"Apart page {page} failed, will retry later (attempt {retry_count + 1}/{max_retries})")
            continue
        
        pageJS = prePage(response, type=1)
        if data := pagecheck(pageJS):
            if not dbinsert:
                return data
            if exist:
                instances = [(model, data[key])
                             for key, model in model_classes.items() if key in data]
                for model, update_values in instances:
                    logging.info(f"Apart page {page}, table {model} is updating")
                    DB.update(model, {'cian_id': page}, update_values)
            else:
                instances = [model(**data[key])
                             for key, model in model_classes.items() if key in data]
                logging.info(f"Apart page {page} is adding")
                DB.insert(*instances)
            pages_cnt += 1
            # Удаляем из списка неудачных при успехе
            if page in failed_pages:
                del failed_pages[page]
        else:
            failed_pages[page] = retry_count + 1
            if retry_count + 1 < max_retries:
                logging.info(f"Apart page {page} parse failed, will retry later (attempt {retry_count + 1}/{max_retries})")
        continue
    
    logging.info(f"Apart pages {pagesList} is END. Added: {pages_cnt}, Skipped: {skipped_count}")
    if not pages_cnt:
        return
    return 'OK'
'''

# Читаем файл
with open('/app/app/parser/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Находим начало функции apartPage
import re
pattern = r'def apartPage\(pagesList, dbinsert=True, max_retries=2\):.*?return \'OK\''
match = re.search(pattern, content, re.DOTALL)

if match:
    # Заменяем функцию на правильную версию
    content = content[:match.start()] + correct_apartPage + content[match.end():]
    
    # Записываем обратно
    with open('/app/app/parser/main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✓ Функция apartPage исправлена")
else:
    print("⚠️  Функция apartPage не найдена или уже исправлена")

