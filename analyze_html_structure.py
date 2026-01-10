#!/usr/bin/env python3
"""
Анализ структуры HTML для поиска правильного паттерна pageview
"""
import re
import sys

def analyze_html(html):
    """Анализирует HTML и ищет правильную структуру данных"""
    print("=" * 80)
    print("АНАЛИЗ СТРУКТУРЫ HTML")
    print("=" * 80)
    print(f"Размер HTML: {len(html):,} байт")
    print()
    
    # Текущий паттерн (как в recjson)
    current_pattern = r'"pageview",\s*(\{.*?\})'
    print(f"1. Текущий паттерн: {current_pattern}")
    match = re.search(current_pattern, html, re.DOTALL)
    if match:
        print("   ✓ НАЙДЕН!")
        print(f"   Длина JSON: {len(match.group(1))} символов")
        print(f"   Превью: {match.group(1)[:300]}...")
    else:
        print("   ✗ НЕ НАЙДЕН")
    print()
    
    # Альтернативные паттерны
    print("2. Альтернативные паттерны:")
    patterns = [
        (r'"pageview"\s*,\s*(\{.*?\})', 'pageview без запятой внутри кавычек'),
        (r'["\']pageview["\']\s*,\s*(\{.*?\})', 'pageview с любыми кавычками'),
        (r'a\.ca\(["\']pageview["\'],\s*(\{.*?\})', 'a.ca("pageview", {...})'),
        (r'pageview.*?(\{.*?"page".*?\})', 'pageview с последующим объектом с page'),
        (r'["\']pageview["\']\s*:\s*(\{.*?\})', 'pageview как ключ объекта'),
    ]
    
    found_patterns = []
    for pattern, desc in patterns:
        match = re.search(pattern, html, re.DOTALL)
        if match:
            print(f"   ✓ {desc}: НАЙДЕН!")
            json_len = len(match.group(1))
            print(f"     Длина JSON: {json_len:,} символов")
            if json_len < 2000:
                print(f"     Превью: {match.group(1)[:500]}...")
            found_patterns.append((pattern, desc, match.group(1)))
        else:
            print(f"   ✗ {desc}: не найден")
    print()
    
    # Поиск объекта с ключом "page"
    print("3. Поиск объектов с ключом 'page':")
    page_pattern = r'"page"\s*:\s*(\{.*?\})'
    matches = list(re.finditer(page_pattern, html, re.DOTALL))
    if matches:
        print(f"   ✓ Найдено {len(matches)} объектов с 'page'")
        for i, m in enumerate(matches[:5], 1):
            json_str = m.group(1)
            # Пытаемся найти полный объект
            start = m.start(1)
            end = start + 1
            brackets = 1
            while brackets > 0 and end < len(html):
                if html[end] == '{':
                    brackets += 1
                elif html[end] == '}':
                    brackets -= 1
                end += 1
            
            full_json = html[start:end]
            print(f"   {i}. Позиция: {m.start()}, Длина: {len(full_json)} символов")
            
            # Проверяем, содержит ли он нужные поля
            if '"pageNumber"' in full_json or '"products"' in full_json:
                print(f"      ✓ Содержит нужные поля!")
                print(f"      Превью: {full_json[:300]}...")
            else:
                print(f"      ✗ Не содержит нужных полей")
    else:
        print("   ✗ Объекты с 'page' не найдены")
    print()
    
    # Поиск контекста вокруг pageview
    print("4. Контекст вокруг 'pageview':")
    pageview_matches = list(re.finditer(r'pageview', html, re.IGNORECASE))
    if pageview_matches:
        print(f"   Найдено {len(pageview_matches)} вхождений 'pageview'")
        for i, m in enumerate(pageview_matches[:3], 1):
            start = max(0, m.start() - 300)
            end = min(len(html), m.end() + 300)
            context = html[start:end]
            print(f"   {i}. Позиция {m.start()}:")
            print(f"      ...{context}...")
            print()
    print()
    
    # Поиск products
    print("5. Поиск 'products' массива:")
    products_pattern = r'"products"\s*:\s*(\[.*?\])'
    products_match = re.search(products_pattern, html, re.DOTALL)
    if products_match:
        print(f"   ✓ Найден products массив!")
        products_json = products_match.group(1)
        print(f"   Длина: {len(products_json):,} символов")
        print(f"   Превью: {products_json[:500]}...")
        
        # Ищем контекст вокруг products
        products_pos = products_match.start()
        context_start = max(0, products_pos - 500)
        context_end = min(len(html), products_pos + 1000)
        context = html[context_start:context_end]
        
        # Ищем объект, содержащий products
        # Идем назад от products, чтобы найти начало объекта
        obj_start = context_start
        for i in range(products_pos, max(0, products_pos - 2000), -1):
            if html[i] == '{':
                obj_start = i
                break
        
        # Ищем конец объекта
        obj_end = products_pos
        brackets = 0
        for i in range(products_pos, min(len(html), products_pos + 5000)):
            if html[i] == '{':
                brackets += 1
            elif html[i] == '}':
                brackets -= 1
                if brackets == 0:
                    obj_end = i + 1
                    break
        
        if obj_end > obj_start:
            full_obj = html[obj_start:obj_end]
            print(f"   Полный объект (длина: {len(full_obj):,} символов):")
            print(f"   Превью: {full_obj[:1000]}...")
            
            # Проверяем, содержит ли он page
            if '"page"' in full_obj or '"pageNumber"' in full_obj:
                print(f"   ✓ Объект содержит 'page'!")
                # Это может быть правильная структура
                return full_obj
    else:
        print("   ✗ products массив не найден")
    print()
    
    # Итоговые рекомендации
    print("=" * 80)
    print("РЕКОМЕНДАЦИИ")
    print("=" * 80)
    
    if found_patterns:
        print("Найдены альтернативные паттерны:")
        for pattern, desc, json_str in found_patterns:
            print(f"  - {desc}")
            print(f"    Паттерн: {pattern}")
    else:
        print("Альтернативные паттерны не найдены.")
        print("Возможно, структура изменилась или данные находятся в другом месте.")
    
    print("=" * 80)
    
    return None

if __name__ == "__main__":
    # Читаем HTML из файла или stdin
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            html = f.read()
    else:
        print("Использование: python analyze_html_structure.py <html_file>")
        print("Или: cat html_file | python analyze_html_structure.py")
        sys.exit(1)
    
    analyze_html(html)

