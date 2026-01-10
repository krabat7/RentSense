#!/bin/bash
# Исправление функции apartPage на сервере

cd /root/rentsense && \
docker-compose -f docker-compose.prod.yml exec -T parser python3 << 'PYEOF'
import re

# Читаем файл
with open('/app/app/parser/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Правильная версия функции с правильными отступами
correct_function = '''def apartPage(pagesList, dbinsert=True, max_retries=2):
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

# Ищем начало функции apartPage
start_pattern = r'def apartPage\(pagesList, dbinsert=True, max_retries=2\):'
end_pattern = r'    return \'OK\''

start_match = re.search(start_pattern, content)
if not start_match:
    print("✗ Функция apartPage не найдена")
    exit(1)

# Находим конец функции - ищем последний return 'OK' после начала функции
start_pos = start_match.start()
# Ищем все вхождения return 'OK' после начала функции
remaining = content[start_pos:]
end_match = re.search(r'    return \'OK\'\s*\n', remaining)
if not end_match:
    # Пробуем без переноса строки
    end_match = re.search(r'    return \'OK\'', remaining)
    
if end_match:
    end_pos = start_pos + end_match.end()
    # Заменяем функцию
    new_content = content[:start_pos] + correct_function + '\n\n' + content[end_pos:].lstrip()
    
    with open('/app/app/parser/main.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✓ Функция apartPage заменена")
else:
    print("✗ Не удалось найти конец функции")
    # Попробуем просто исправить отступы на строке 368
    lines = content.split('\n')
    if len(lines) >= 368:
        line_368 = lines[367]  # Индекс 367 для строки 368
        # Проверяем отступы
        if line_368.strip():
            # Должно быть 8 пробелов в начале
            stripped = line_368.lstrip()
            if stripped and not line_368.startswith('        '):
                lines[367] = '        ' + stripped
                new_content = '\n'.join(lines)
                with open('/app/app/parser/main.py', 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print("✓ Отступы на строке 368 исправлены")
            else:
                print(f"⚠️  Строка 368: '{line_368[:50]}'")
        else:
            print("⚠️  Строка 368 пустая")
PYEOF

