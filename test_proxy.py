import curl_cffi.requests as requests
from bs4 import BeautifulSoup
import json
import re
import pandas as pd
from datetime import datetime
from urllib.parse import urljoin
import time

# ===== НАСТРОЙКИ =====
PROXY = "http://5ZT0gXJzXALl:1eJvGY40@pool.proxy.market:10000"
PROXIES = {"http": PROXY, "https": PROXY}

# Заголовки для имитации реального браузера
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.7499.193 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Referer": "https://www.cian.ru/",
    "Sec-Ch-Ua": '"Google Chrome";v="143", "Chromium";v="143", "Not?A_Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Upgrade-Insecure-Requests": "1",
}

# ===== ФУНКЦИИ =====

def parse_cian_card(card):
    """Парсит одну карточку объявления Циана"""
    result = {
        'id': '',
        'title': '',
        'price': '',
        'price_rub': 0,
        'address': '',
        'area': '',
        'area_m2': 0,
        'rooms': '',
        'floor': '',
        'total_floors': '',
        'description': '',
        'link': '',
        'metro': '',
        'district': '',
        'agency': '',
        'parsed_time': datetime.now().isoformat()
    }
    
    try:
        # ID из data-id или ссылки
        if card.get('data-id'):
            result['id'] = card['data-id']
        
        # Ссылка на объявление
        link_elem = card.find('a', href=re.compile(r'/rent/flat/\d+/'))
        if link_elem:
            href = link_elem.get('href', '')
            result['link'] = urljoin('https://cian.ru', href)
            
            # Извлекаем ID из ссылки
            match = re.search(r'/(\d+)/', href)
            if match:
                result['id'] = match.group(1)
        
        # Заголовок
        title_elem = card.find(['span', 'div'], attrs={'data-mark': 'OfferTitle'})
        if not title_elem:
            title_elem = card.find(['h3', 'h2', 'span'], class_=re.compile(r'title|header', re.I))
        if title_elem:
            result['title'] = title_elem.get_text(strip=True)
        
        # Цена
        price_elem = card.find(['span', 'div'], attrs={'data-mark': 'MainPrice'})
        if not price_elem:
            # Ищем по тексту с символом рубля
            price_text = card.find(string=re.compile(r'₽'))
            if price_text:
                result['price'] = price_text.strip()
            else:
                # Ищем по классам
                price_elem = card.find(['span', 'div'], class_=re.compile(r'price|Price|mainPrice', re.I))
        
        if price_elem:
            result['price'] = price_elem.get_text(strip=True)
        
        # Извлекаем числовое значение цены
        if result['price']:
            match = re.search(r'(\d[\d\s]+)', result['price'].replace(' ', ''))
            if match:
                try:
                    result['price_rub'] = int(match.group(1).replace(' ', ''))
                except:
                    pass
        
        # Адрес
        address_elem = card.find(['div', 'span'], attrs={'data-name': 'AddressContainer'})
        if not address_elem:
            address_elem = card.find(['div', 'span'], class_=re.compile(r'address|geo|location', re.I))
        if address_elem:
            result['address'] = address_elem.get_text(' ', strip=True)
        
        # Метро и район
        metro_elem = card.find(['div', 'span'], class_=re.compile(r'metro|underground', re.I))
        if metro_elem:
            result['metro'] = metro_elem.get_text(strip=True)
        
        district_elem = card.find(['div', 'span'], class_=re.compile(r'district|region', re.I))
        if district_elem:
            result['district'] = district_elem.get_text(strip=True)
        
        # Характеристики (площадь, этаж, комнаты)
        features_container = card.find('div', attrs={'data-name': 'OfferSpec'})
        if not features_container:
            features_container = card.find('div', class_=re.compile(r'features|specs|info', re.I))
        
        if features_container:
            features_text = features_container.get_text(' ', strip=True)
            result['description'] = features_text[:200]
            
            # Извлекаем площадь
            area_match = re.search(r'(\d+[,.]?\d*)\s*м[²2]', features_text)
            if area_match:
                result['area'] = area_match.group(0)
                try:
                    result['area_m2'] = float(area_match.group(1).replace(',', '.'))
                except:
                    pass
            
            # Извлекаем этажи
            floor_match = re.search(r'(\d+)\s*/\s*(\d+)\s*эт', features_text)
            if floor_match:
                result['floor'] = floor_match.group(1)
                result['total_floors'] = floor_match.group(2)
            
            # Комнаты
            rooms_match = re.search(r'(\d+)-?(комн|к)', features_text, re.I)
            if rooms_match:
                result['rooms'] = rooms_match.group(0)
        
        # Агентство
        agency_elem = card.find(['div', 'span'], class_=re.compile(r'agency|realtor|company', re.I))
        if agency_elem:
            result['agency'] = agency_elem.get_text(strip=True)
        
        # Если не нашли площадь в описании, ищем отдельно
        if not result['area']:
            area_elem = card.find(string=re.compile(r'м[²2]'))
            if area_elem:
                result['area'] = area_elem.strip()
        
    except Exception as e:
        print(f"Ошибка парсинга карточки: {e}")
    
    return result

def parse_cian_page(url, page_num=1):
    """Парсит одну страницу Циана"""
    print(f"\n📄 Страница {page_num}: {url[:80]}...")
    
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            proxies=PROXIES,
            timeout=15,
            impersonate="chrome110"
        )
        
        if response.status_code != 200:
            print(f"❌ Ошибка {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем все карточки объявлений
        cards = soup.find_all(['article', 'div'], attrs={'data-name': 'CardComponent'})
        if not cards:
            cards = soup.find_all('div', attrs={'data-testid': 'offer-card'})
        
        print(f"   Найдено карточек: {len(cards)}")
        
        offers = []
        for i, card in enumerate(cards[:30]):  # Ограничиваем 30 на странице
            offer = parse_cian_card(card)
            if offer.get('id'):
                offers.append(offer)
                if i < 3:  # Показываем первые 3 для примера
                    print(f"   {i+1}. ID {offer['id']}: {offer.get('title', '')[:40]}... - {offer.get('price', '')}")
        
        return offers
        
    except Exception as e:
        print(f"❌ Ошибка при парсинге страницы: {e}")
        return []

def parse_multiple_pages(base_url, max_pages=3):
    """Парсит несколько страниц Циана"""
    all_offers = []
    
    for page in range(1, max_pages + 1):
        if page == 1:
            url = base_url
        else:
            url = f"{base_url}&p={page}"
        
        offers = parse_cian_page(url, page)
        all_offers.extend(offers)
        
        # Пауза между страницами
        if page < max_pages and offers:
            delay = 3
            print(f"   ⏳ Ждем {delay} секунд перед следующей страницей...")
            time.sleep(delay)
    
    return all_offers

def save_results(offers, filename_prefix="cian_offers"):
    """Сохраняет результаты в JSON и CSV"""
    if not offers:
        print("❌ Нет данных для сохранения")
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # JSON
    json_filename = f"{filename_prefix}_{timestamp}.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(offers, f, ensure_ascii=False, indent=2)
    print(f"✅ Сохранено в JSON: {json_filename}")
    
    # CSV
    csv_filename = f"{filename_prefix}_{timestamp}.csv"
    df = pd.DataFrame(offers)
    
    # Выбираем важные колонки
    important_cols = ['id', 'title', 'price', 'price_rub', 'area', 'area_m2', 
                     'rooms', 'floor', 'address', 'metro', 'link']
    available_cols = [col for col in important_cols if col in df.columns]
    
    if available_cols:
        df[available_cols].to_csv(csv_filename, index=False, encoding='utf-8-sig')
        print(f"✅ Сохранено в CSV: {csv_filename}")
    else:
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        print(f"✅ Сохранено в CSV (все колонки): {csv_filename}")
    
    return json_filename, csv_filename

def analyze_results(offers):
    """Анализирует собранные данные"""
    if not offers:
        return
    
    df = pd.DataFrame(offers)
    
    print(f"\n📊 АНАЛИЗ РЕЗУЛЬТАТОВ:")
    print(f"   Всего объявлений: {len(offers)}")
    
    if 'price_rub' in df.columns:
        avg_price = df['price_rub'].mean()
        min_price = df['price_rub'].min()
        max_price = df['price_rub'].max()
        print(f"   Средняя цена: {avg_price:,.0f} ₽")
        print(f"   Минимальная цена: {min_price:,.0f} ₽")
        print(f"   Максимальная цена: {max_price:,.0f} ₽")
    
    if 'area_m2' in df.columns:
        avg_area = df['area_m2'].mean()
        print(f"   Средняя площадь: {avg_area:.1f} м²")
    
    if 'rooms' in df.columns:
        room_counts = df['rooms'].value_counts()
        print(f"   Распределение по комнатам:")
        for rooms, count in room_counts.head().items():
            print(f"     {rooms}: {count} объявлений")
    
    print(f"\n🎯 ПРИМЕРЫ ОБЪЯВЛЕНИЙ:")
    for i, offer in enumerate(offers[:3]):
        print(f"\n{i+1}. {offer.get('title', 'Без названия')[:60]}...")
        print(f"   Цена: {offer.get('price', 'Нет')}")
        print(f"   Площадь: {offer.get('area', 'Нет')}")
        print(f"   Адрес: {offer.get('address', 'Нет')[:50]}...")
        print(f"   Ссылка: {offer.get('link', 'Нет')[:80]}...")

# ===== ОСНОВНАЯ ПРОГРАММА =====

def main():
    print("=" * 60)
    print("🏠 ПАРСЕР ЦИАНА С curl_cffi И РОТИРУЮЩИМ ПРОКСИ")
    print("=" * 60)
    
    # Базовый URL (аренда квартир в Москве)
    BASE_URL = "https://www.cian.ru/cat.php?deal_type=rent&engine_version=2&offer_type=flat&region=1&type=4"
    
    print(f"\n🔍 Начинаем парсинг...")
    print(f"📡 Используем прокси: pool.proxy.market:10000")
    print(f"🔄 Ротация: 5 минут")
    
    # Парсим несколько страниц
    offers = parse_multiple_pages(BASE_URL, max_pages=2)
    
    if offers:
        print(f"\n✅ Успешно собрано {len(offers)} объявлений")
        
        # Сохраняем
        json_file, csv_file = save_results(offers)
        
        # Анализируем
        analyze_results(offers)
        
        print(f"\n💾 Результаты сохранены в:")
        print(f"   JSON: {json_file}")
        print(f"   CSV: {csv_file}")
    else:
        print("❌ Не удалось собрать объявления")
    
    print("\n" + "=" * 60)
    print("🎉 Парсинг завершен!")
    print("=" * 60)

if __name__ == "__main__":
    # Установите зависимости если нужно:
    # pip install curl_cffi beautifulsoup4 pandas
    
    main()