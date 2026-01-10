import sys
sys.path.insert(0, '.')

from app.parser.main import listPages

def test_list_parsing():
    print("Тестирование парсинга списка объявлений...")
    print("Проверяю первую страницу списка аренды")
    
    result = listPages(1, sort=None, rooms=None)
    
    if result == 'END':
        print("✗ Страница пустая или достигнут конец")
        return False
    elif isinstance(result, list) and len(result) > 0:
        print(f"✓ Найдено {len(result)} объявлений на странице")
        print(f"Первые 5 ID: {result[:5]}")
        return True
    else:
        print("✗ Не удалось получить список объявлений")
        return False

if __name__ == "__main__":
    test_list_parsing()


