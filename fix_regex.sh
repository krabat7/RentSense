#!/bin/bash
cd /root/rentsense

echo "=== Исправление регулярного выражения в prePage ==="

# Исправляем проблемную строку с паттерном
sed -i 's/pattern1 = r'"'"'"page"\\s*:\\s*(\\{[^{}]*"pageNumber"[^{}]*"products"[^{}]*\\})'"'"'/pattern1 = r'"'"'"page"\\s*:\\s*\\{'"'"'/g' app/parser/main.py

# Также нужно исправить логику извлечения объекта
python3 << 'PYTHON_SCRIPT'
import re

with open('app/parser/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем блок обработки pattern1
old_block = r'pattern1 = r'"'"'"page"\s*:\s*\{'"'"'.*?if brackets == 0:.*?logging\.warning\(f"Failed to parse page JSON \(variant 1\): \{e\}"\)'

new_block = '''pattern1 = r'"page"\\s*:\\s*\\{'
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
                    logging.warning(f"Failed to parse page JSON (variant 1): {e}")'''

# Находим начало функции prePage и заменяем весь блок else
pattern = r'(def prePage\(data, type=0\):.*?if type:.*?return pageJS\s+else:).*?(# Вариант 2: Старый паттерн)'

def replace_func(match):
    return match.group(1) + '\n        ' + new_block + '\n        \n        ' + match.group(2)

content = re.sub(pattern, replace_func, content, flags=re.DOTALL)

with open('app/parser/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Функция prePage исправлена")
PYTHON_SCRIPT

echo ""
echo "Проверка синтаксиса Python..."
python3 -m py_compile app/parser/main.py && echo "✓ Синтаксис корректен" || echo "✗ Ошибка синтаксиса"

echo ""
echo "Перезапуск парсера..."
docker-compose -f docker-compose.prod.yml restart parser
echo "✓ Парсер перезапущен"

