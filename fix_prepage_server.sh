#!/bin/bash
cd /root/rentsense

# Создаем Python скрипт для замены функции prePage
python3 << 'PYTHON_SCRIPT'
import re

# Читаем текущий файл
with open('app/parser/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Новая функция prePage
new_prepage = '''def prePage(data, type=0):
    if type:
        # Для страницы объявления ищем "offerData"
        key = '"offerData":'
        if pageJS := recjson(rf'{key}\\s*(\\{\\{.*?\\}\\})', data):
            return pageJS
    else:
        # Для списка страниц структура изменилась - ищем объект с ключом "page", 
        # который содержит "pageNumber" и "products"
        # Старый паттерн "pageview", больше не работает
        
        # Вариант 1: Ищем начало объекта "page": {...}
        # Находим позицию "page": и затем ищем открывающую скобку
        pattern1 = r'"page"\\s*:\\s*\\{'
        match = re.search(pattern1, data)
        if match:
            # Находим начало объекта (открывающая скобка после двоеточия)
            start = match.end() - 1  # Позиция открывающей скобки
            end = start + 1
            brackets = 1
            max_search = min(len(data), start + 1000000)  # Ограничиваем поиск до 1MB
            
            # Считаем скобки для извлечения полного объекта
            while brackets > 0 and end < max_search:
                if data[end] == '{':
                    brackets += 1
                elif data[end] == '}':
                    brackets -= 1
                end += 1
            
            if brackets == 0:  # Нашли полный объект
                full_json = data[start:end]
                try:
                    pageJS = json.loads(full_json)
                    if 'pageNumber' in pageJS and 'products' in pageJS:
                        logging.info(f"Found page object with pageNumber={pageJS.get('pageNumber')} and {len(pageJS.get('products', []))} products")
                        return {'page': pageJS}
                except Exception as e:
                    logging.warning(f"Failed to parse page JSON (variant 1): {e}")
        
        # Вариант 2: Старый паттерн (на случай, если где-то еще работает)
        key = '"pageview",'
        if pageJS := recjson(rf'{key}\\s*(\\{\\{.*?\\}\\})', data):
            return pageJS
    
    return {}'''

# Находим и заменяем функцию prePage
pattern = r'def prePage\(data, type=0\):.*?return \{\}'
new_content = re.sub(pattern, new_prepage, content, flags=re.DOTALL)

# Записываем обратно
with open('app/parser/main.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✓ Функция prePage обновлена")
PYTHON_SCRIPT

echo "Перезапуск парсера..."
docker-compose -f docker-compose.prod.yml restart parser
echo "✓ Парсер перезапущен"
echo ""
echo "Проверка логов через 30 секунд..."
sleep 30
docker-compose -f docker-compose.prod.yml logs parser | tail -30

