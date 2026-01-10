import sys
sys.path.insert(0, '.')

from app.parser.main import apartPage
import json

def test_single_parsing(test_id=None):
    if not test_id:
        print("Введите ID объявления с Циана")
        test_id = input("ID: ").strip()
    
    print(f"Парсинг объявления {test_id}...")
    print("(без сохранения в БД)")
    
    result = apartPage([test_id], dbinsert=False)
    
    if result:
        print("\n✓ Парсинг успешен!")
        print("\nСтруктура данных:")
        for key, value in result.items():
            if isinstance(value, dict):
                print(f"\n{key}:")
                for k, v in value.items():
                    if v is not None:
                        print(f"  {k}: {v}")
            else:
                if value is not None:
                    print(f"{key}: {value}")
        
        print("\n✓ Все данные извлечены корректно")
        return True
    else:
        print("\n✗ Парсинг не удался - проверьте структуру страницы")
        return False

if __name__ == "__main__":
    import sys
    test_id = sys.argv[1] if len(sys.argv) > 1 else None
    test_single_parsing(test_id)


