#!/bin/bash
cd /root/rentsense

echo "=== Обновление app/parser/main.py с исправленным паттерном ==="

# Создаем временный файл с исправленным кодом
cat > /tmp/main_fixed.py << 'MAIN_EOF'
import logging
import random
import time
import re
import json
from playwright.sync_api import sync_playwright
from .database import DB, model_classes
from .pagecheck import pagecheck
from .tools import headers, proxyDict, proxyBlockedTime, check_and_unfreeze_proxies, recjson

URL = 'https://www.cian.ru'

_playwright = None
_browser = None

def _get_browser():
    global _playwright, _browser
    if _browser is None:
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(headless=True)
    return _browser

def close_browser():
    global _playwright, _browser
    if _browser:
        _browser.close()
        _browser = None
    if _playwright:
        _playwright.stop()
        _playwright = None

def getResponse(page, type=0, respTry=5, sort=None, rooms=None, dbinsert=True):
    # Периодически проверяем и размораживаем заблокированные прокси
    if respTry == 5:  # Только при первом вызове, чтобы не проверять слишком часто
        check_and_unfreeze_proxies()
    
    # Получаем список доступных прокси (которые не заблокированы)
    available_proxies = {k: v for k, v in proxyDict.items() if v <= time.time()}
    
    # Если доступных прокси меньше 2, ждем освобождения
    if len(available_proxies) < 2:
        count = min(len(proxyDict) - 1, 2)
        mintime = sorted(proxyDict.values())[count]
        if (mintime > (timenow := time.time())):
            misstime = mintime - timenow
            if not dbinsert and misstime >= 10:
                return
            logging.info(f'No available proxies, waiting {misstime:.2f} seconds')
            time.sleep(misstime)
            # Обновляем список после ожидания
            available_proxies = {k: v for k, v in proxyDict.items() if v <= time.time()}
    
    # Выбираем прокси, который дольше всего не использовался (с наименьшим временем блокировки)
    # Это обеспечивает равномерное распределение нагрузки между прокси
    if available_proxies:
        proxy = min(available_proxies.items(), key=lambda x: x[1])[0]
    else:
        # Если все прокси заблокированы, используем случайный (fallback)
        proxy = random.choice([k for k, v in proxyDict.items() if v <= time.time()])

    url = f'{URL}/rent/flat/{page}/' if type else f'{URL}/cat.php'
    if not type:
        params = {
            'deal_type': 'rent',
            'offer_type': 'flat',
            'p': page,
            'region': 1,
        }
        if rooms:
            params[rooms] = 1
        if sort:
            params['sort'] = sort
        url += '?' + '&'.join([f'{k}={v}' for k, v in params.items()])

    try:
        start = time.time()
        browser = _get_browser()
        
        context_options = {
            'user_agent': random.choice(headers)['User-Agent'],
        }
        
        if proxy:
            from urllib.parse import urlparse
            parsed = urlparse(proxy)
            context_options['proxy'] = {
                'server': f'{parsed.scheme}://{parsed.hostname}:{parsed.port}',
                'username': parsed.username,
                'password': parsed.password,
            }
        
        context = browser.new_context(**context_options)
        page_obj = context.new_page()
        
        try:
            try:
                response_obj = page_obj.goto(url, wait_until='domcontentloaded', timeout=45000)
            except Exception as e:
                logging.warning(f"Goto timeout/error, trying to get content anyway: {e}")
                response_obj = None
            
            if response_obj and response_obj.status != 200:
                logging.error(f"GetResponse Page {page} | Retry: {respTry} | {response_obj.status}")
                if response_obj.status in (403, 429):
                    # Увеличена задержка для 403/429 до 10 минут
                    proxyDict[proxy] = time.time() + (10 * 60)
                    proxyBlockedTime[proxy] = time.time()  # Запоминаем время блокировки
                elif response_obj.status == 404:
                    return None
                else:
                    proxyDict[proxy] = time.time() + (3 * 60)  # Увеличена задержка до 3 минут
                    proxyBlockedTime[proxy] = time.time()
                if respTry > 0:
                    return getResponse(page, type, respTry - 1, sort, rooms, dbinsert)
                return None
            
            time.sleep(5)
            html = page_obj.content()
            current_url = page_obj.url
            logging.info(f'Playwright time {proxy or "no proxy"} = {(time.time() - start):.2f}')
            
            # Дополнительная задержка после получения контента для снижения нагрузки на прокси
            time.sleep(3)
        finally:
            page_obj.close()
            context.close()
        
        if 'cian.ru' not in current_url:
            logging.error(f"Redirected away from cian.ru: {current_url}")
            if respTry > 0:
                return getResponse(page, type, respTry - 1, sort, rooms, dbinsert)
            return None
        
        if '"offerData":' in html:
            # Увеличена задержка после успешного запроса до 30 секунд
            proxyDict[proxy] = time.time() + 30
            proxyBlockedTime[proxy] = 0  # Сбрасываем время блокировки при успехе
            return html
        
        if len(html) < 50000 and 'captcha' in html.lower():
            logging.warning(f"Captcha detected for page {page}, HTML too short: {len(html)}")
            # Увеличена задержка для captcha до 15 минут
            proxyDict[proxy] = time.time() + (15 * 60)
            proxyBlockedTime[proxy] = time.time()  # Запоминаем время блокировки
            if respTry > 0:
                return getResponse(page, type, respTry - 1, sort, rooms, dbinsert)
            return None
        
        # Для списка страниц (type=0) проверяем наличие "page" или "pageview"
        # Для страницы объявления (type=1) проверяем наличие "offerData"
        if not type:  # Список страниц
            if len(html) < 50000:
                logging.warning(f"HTML too short for list page {page}: {len(html)} bytes (likely captcha or error)")
                if respTry > 0:
                    return getResponse(page, type, respTry - 1, sort, rooms, dbinsert)
                return None
            # Проверяем наличие объекта с "page" (новый формат) или "pageview" (старый формат)
            if '"page"' not in html and '"pageview"' not in html and '"pageview",' not in html:
                logging.warning(f"No 'page' or 'pageview' found in HTML for page {page}, length: {len(html)}")
                if respTry > 0:
                    return getResponse(page, type, respTry - 1, sort, rooms, dbinsert)
                return None
        else:  # Страница объявления
            if len(html) < 100000:
                logging.warning(f"No offerData found, HTML too short: {len(html)}")
                if respTry > 0:
                    return getResponse(page, type, respTry - 1, sort, rooms, dbinsert)
                return None
        
        # Увеличена задержка после успешного запроса до 30 секунд
        proxyDict[proxy] = time.time() + 30
        proxyBlockedTime[proxy] = 0  # Сбрасываем время блокировки при успехе
        return html
        
    except Exception as e:
        proxyDict[proxy] = time.time() + (3 * 60)  # Увеличена задержка до 3 минут
        proxyBlockedTime[proxy] = time.time()
        logging.error(f'Proxy {proxy}: {e}')
        if respTry > 0:
            return getResponse(page, type, respTry - 1, sort, rooms, dbinsert)
        return None


def prePage(data, type=0):
    if type:
        # Для страницы объявления ищем "offerData"
        key = '"offerData":'
        if pageJS := recjson(rf'{key}\s*(\{{.*?\}})', data):
            return pageJS
    else:
        # Для списка страниц структура изменилась - ищем объект с ключом "page", 
        # который содержит "pageNumber" и "products"
        # Старый паттерн "pageview", больше не работает
        
        # Вариант 1: Ищем начало объекта "page": {...}
        # Находим позицию "page": и затем ищем открывающую скобку
        pattern1 = r'"page"\s*:\s*\{'
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
        if pageJS := recjson(rf'{key}\s*(\{{.*?\}})', data):
            return pageJS
    
    return {}


def listPages(page, sort=None, rooms=None):
    pagesList = []
    if not (response := getResponse(page, type=0, sort=sort, rooms=rooms)):
        return []
    pageJS = prePage(response, type=0)
    # pageJS теперь имеет структуру {'page': {...}} или старую структуру
    page_obj = pageJS.get('page', pageJS)  # Поддержка старого и нового формата
    if page_obj.get('pageNumber') != page:
        logging.info(f"Prewiew page {page} is END")
        return 'END'
    if products := page_obj.get('products'):
        for i in products:
            if id := i.get('cianId'):
                logging.info(f"Prewiew page {id} appended")
                pagesList.append(id)
        return pagesList
    logging.info(f"Prewiew page {page} is None")
    return []


def apartPage(pagesList, dbinsert=True):
    pages_cnt = 0
    for page in pagesList:
        exist = False
        if dbinsert and DB.select(model_classes['offers'], filter_by={'cian_id': page}):
            exist = True
            logging.info(f"Apart page {page} already exists")
            continue
        if not (response := getResponse(page, type=1, dbinsert=dbinsert)):
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
        continue
    logging.info(f"Apart pages {pagesList} is END")
    if not pages_cnt:
        return
    return 'OK'
MAIN_EOF

# Копируем исправленный файл
cp /tmp/main_fixed.py app/parser/main.py
rm /tmp/main_fixed.py

echo "✓ Файл main.py обновлен"
echo ""
echo "Проверка синтаксиса Python..."
python3 -m py_compile app/parser/main.py && echo "✓ Синтаксис корректен" || echo "✗ Ошибка синтаксиса"

echo ""
echo "Перезапуск парсера..."
docker-compose -f docker-compose.prod.yml restart parser
echo "✓ Парсер перезапущен"

echo ""
echo "Проверка логов через 30 секунд..."
sleep 30
docker-compose -f docker-compose.prod.yml logs parser | tail -40

