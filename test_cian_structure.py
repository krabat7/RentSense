import requests
import sys
sys.path.insert(0, '.')

from app.parser.tools import recjson, headers
import random

def check_cian_structure(test_id=None):
    if not test_id:
        print("Введите ID объявления с Циана (например, из URL: cian.ru/rent/flat/12345678/)")
        test_id = input("ID: ").strip()
    
    url = f"https://www.cian.ru/rent/flat/{test_id}/"
    print(f"Проверяю URL: {url}")
    
    try:
        response = requests.get(url, headers=random.choice(headers), timeout=10)
        print(f"Status code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Ошибка: страница не доступна")
            return False
        
        if '"offerData":' in response.text:
            print("✓ offerData найден в HTML")
            pageJS = recjson(r'"offerData":\s*(\{.*?\})', response.text)
            if pageJS and 'offer' in pageJS:
                print("✓ Структура offer найдена")
                offer = pageJS['offer']
                print(f"Ключи в offer (первые 15): {list(offer.keys())[:15]}")
                
                if 'cianId' in offer:
                    print(f"✓ cianId найден: {offer.get('cianId')}")
                if 'priceTotalRur' in offer:
                    print(f"✓ priceTotalRur найден: {offer.get('priceTotalRur')}")
                if 'dealType' in offer:
                    print(f"✓ dealType найден: {offer.get('dealType')}")
                
                return True
            else:
                print("✗ Структура offer не найдена в JSON")
                return False
        else:
            print("✗ offerData не найден - возможно изменилась структура страницы")
            print("Проверяю альтернативные варианты...")
            if 'pageview' in response.text:
                print("Найден pageview, возможно это страница списка")
            return False
            
    except Exception as e:
        print(f"Ошибка при запросе: {e}")
        return False

if __name__ == "__main__":
    import sys
    test_id = sys.argv[1] if len(sys.argv) > 1 else None
    check_cian_structure(test_id)


