import logging
import random
import time
import re
import json
from playwright.sync_api import sync_playwright
from .database import DB, model_classes
from .pagecheck import pagecheck
from .tools import headers, proxyDict, proxyBlockedTime, proxyErrorCount, check_and_unfreeze_proxies, recjson

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
    if len(available_proxies) == 0 and respTry == 5:  # Логируем только при первом вызове
        logging.warning(f'getResponse: No available proxies for page={page}, type={type}, dbinsert={dbinsert}, total_proxies={len(proxyDict)}')
    
    # Если доступных прокси меньше 1, ждем освобождения (было 2, уменьшено для ускорения)
    # Но не ждем больше 60 секунд, чтобы не блокировать парсинг
    if len(available_proxies) < 1:
        count = min(len(proxyDict) - 1, 1)
        mintime = sorted(proxyDict.values())[count]
        if (mintime > (timenow := time.time())):
            misstime = min(mintime - timenow, 60)  # Максимум 60 секунд ожидания
            # УБИРАЕМ ранний возврат - всегда ждем, даже если dbinsert=False
            # Это позволяет парсеру работать даже когда все прокси заблокированы
            if misstime > 0:
                logging.info(f'No available proxies, waiting {misstime:.2f} seconds (max 60s)')
                time.sleep(misstime)
            # Обновляем список после ожидания
            available_proxies = {k: v for k, v in proxyDict.items() if v <= time.time()}
    
    # Выбираем прокси, который дольше всего не использовался (с наименьшим временем блокировки)
    # Это обеспечивает равномерное распределение нагрузки между прокси
    if available_proxies:
        proxy = min(available_proxies.items(), key=lambda x: x[1])[0]
    else:
        # Если все прокси заблокированы после ожидания, используем пустой прокси (без прокси)
        # или выбираем тот, который освободится раньше всех
        if len(proxyDict) > 1:  # Есть прокси в словаре
            # Выбираем прокси с наименьшим временем блокировки (освободится раньше всех)
            earliest_proxy = min(proxyDict.items(), key=lambda x: x[1])
            if earliest_proxy[1] <= time.time() + 300:  # Если освободится в течение 5 минут
                proxy = earliest_proxy[0]
                logging.warning(f'All proxies blocked, using earliest available: {proxy[:30]}... (unlocks in {earliest_proxy[1] - time.time():.0f}s)')
            else:
                # Если все прокси заблокированы надолго, используем пустой прокси
                proxy = ''
                logging.warning('All proxies blocked for >5 minutes, using no proxy')
        else:
            # Нет прокси в словаре, используем пустой
            proxy = ''
            logging.warning('No proxies configured, using no proxy')

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
                    # Увеличиваем счетчик ошибок
                    proxyErrorCount[proxy] = proxyErrorCount.get(proxy, 0) + 1
                    
                    # Блокируем только после 2-й ошибки подряд (не сразу после первой)
                    if proxyErrorCount[proxy] >= 2:
                        # Уменьшена задержка для 403/429 до 10 минут
                        proxyDict[proxy] = time.time() + (10 * 60)
                        proxyBlockedTime[proxy] = time.time()
                        logging.warning(f"Proxy {proxy[:30]}... blocked after {proxyErrorCount[proxy]} errors")
                        proxyErrorCount[proxy] = 0  # Сбрасываем счетчик
                    else:
                        # После первой ошибки - небольшая задержка (2 минуты)
                        proxyDict[proxy] = time.time() + (2 * 60)
                        logging.info(f"Proxy {proxy[:30]}... warning ({proxyErrorCount[proxy]}/2 errors)")
                elif response_obj.status == 404:
                    return None
                else:
                    # Для других ошибок - небольшая задержка
                    proxyDict[proxy] = time.time() + (2 * 60)
                    proxyBlockedTime[proxy] = time.time()
                if respTry > 0:
                    return getResponse(page, type, respTry - 1, sort, rooms, dbinsert)
                return None
            
            time.sleep(2)  # Уменьшено с 5 до 2 секунд для ускорения
            html = page_obj.content()
            current_url = page_obj.url
            logging.info(f'Playwright time {proxy or "no proxy"} = {(time.time() - start):.2f}')
            
            # Дополнительная задержка после получения контента для снижения нагрузки на прокси
            time.sleep(2)  # Уменьшено с 5 до 2 секунд для ускорения
        finally:
            page_obj.close()
            context.close()
        
        if 'cian.ru' not in current_url:
            logging.error(f"Redirected away from cian.ru: {current_url}")
            if respTry > 0:
                return getResponse(page, type, respTry - 1, sort, rooms, dbinsert)
            return None
        
        if '"offerData":' in html:
            # Оптимизированная задержка после успешного запроса: 28 секунд (увеличено с 20 на основе анализа - 56% ошибок)
            proxyDict[proxy] = time.time() + 28
            proxyBlockedTime[proxy] = 0  # Сбрасываем время блокировки при успехе
            proxyErrorCount[proxy] = 0  # Сбрасываем счетчик ошибок при успехе
            return html
        
        if len(html) < 50000 and 'captcha' in html.lower():
            logging.warning(f"Captcha detected for page {page}, HTML too short: {len(html)}")
            # Уменьшена задержка для captcha до 15 минут
            proxyDict[proxy] = time.time() + (15 * 60)
            proxyBlockedTime[proxy] = time.time()  # Запоминаем время блокировки
            if respTry > 0:
                return getResponse(page, type, respTry - 1, sort, rooms, dbinsert)
            return None
        
        # Для списка страниц (type=0) проверяем наличие "pageview"
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
        
        # Оптимизированная задержка после успешного запроса: 28 секунд (увеличено с 20 на основе анализа - 56% ошибок)
        proxyDict[proxy] = time.time() + 28
        proxyBlockedTime[proxy] = 0  # Сбрасываем время блокировки при успехе
        proxyErrorCount[proxy] = 0  # Сбрасываем счетчик ошибок при успехе
        return html
        
    except Exception as e:
        proxyDict[proxy] = time.time() + (2 * 60)  # Увеличена задержка до 2 минут
        proxyBlockedTime[proxy] = time.time()
        logging.error(f'Proxy {proxy}: {e}')
        if respTry > 0:
            return getResponse(page, type, respTry - 1, sort, rooms, dbinsert)
        return None


def prePage(data, type=0):
    if type:
        # Для страницы объявления ищем "offerData"
        key = '"offerData":'
        pattern = key + r'\s*(\{.*?\})'
        if pageJS := recjson(pattern, data):
            return pageJS
    else:
        # Для списка страниц структура изменилась - ищем объект с ключом "page", 
        # который содержит "pageNumber" и "products"
        # Старый паттерн "pageview", больше не работает
        
        # Вариант 1: Ищем объект, который содержит "pageNumber" и "products" одновременно
        # Используем более надежный подход - ищем участок HTML, где есть оба поля
        try:
            # Сначала проверяем, есть ли вообще "pageNumber" и "products" в HTML
            has_pageNumber = '"pageNumber"' in data
            has_products = '"products"' in data
            logging.info(f"HTML check: pageNumber={has_pageNumber}, products={has_products}, HTML length={len(data)}")
            
            if not has_pageNumber or not has_products:
                logging.warning(f"Missing required fields: pageNumber={has_pageNumber}, products={has_products}")
            
            # Ищем позицию, где есть и "pageNumber", и "products" рядом
            # Сначала находим все вхождения "pageNumber"
            pageNumber_pattern = r'"pageNumber"\s*:\s*\d+'
            pageNumber_matches = list(re.finditer(pageNumber_pattern, data))
            
            logging.info(f"Found {len(pageNumber_matches)} 'pageNumber' matches")
            
            # Для каждого найденного "pageNumber" проверяем, есть ли рядом "products"
            for idx, pn_match in enumerate(pageNumber_matches):
                pn_start = pn_match.start()
                # Ищем "products" в пределах 100000 символов после "pageNumber"
                search_end = min(len(data), pn_start + 100000)
                search_area = data[pn_start:search_end]
                
                if '"products"' in search_area or '"products":' in search_area:
                    # Нашли область, где есть и pageNumber, и products
                    logging.info(f"Match {idx+1}: Found 'products' near 'pageNumber' at position {pn_start}")
                    
                    # Ищем начало объекта, который содержит оба поля
                    # Используем более надежный подход - ищем объект, который содержит оба поля
                    # Начинаем поиск с позиции перед pageNumber
                    search_start = max(0, pn_start - 50000)
                    search_end = min(len(data), pn_start + 100000)
                    search_area = data[search_start:search_end]
                    
                    # Ищем все открывающие скобки в этой области
                    bracket_positions = []
                    for i, char in enumerate(search_area):
                        if char == '{':
                            bracket_positions.append(search_start + i)
                    
                    # Проверяем каждый объект, начиная с самого большого (последнего открывающего скобки)
                    for bracket_pos in reversed(bracket_positions):
                        # Извлекаем объект, начиная с этой позиции
                        start = bracket_pos
                        end = start + 1
                        brackets = 1
                        max_search = min(len(data), start + 1000000)
                        
                        while brackets > 0 and end < max_search:
                            if data[end] == '{':
                                brackets += 1
                            elif data[end] == '}':
                                brackets -= 1
                            end += 1
                        
                        if brackets == 0:
                            # Проверяем, содержит ли этот объект оба поля
                            obj_text = data[start:end]
                            if '"pageNumber"' in obj_text and '"products"' in obj_text:
                                try:
                                    pageJS = json.loads(obj_text)
                                    # Проверяем, есть ли pageNumber и products на верхнем уровне
                                    if 'pageNumber' in pageJS and 'products' in pageJS:
                                        logging.info(f"Found page object with pageNumber={pageJS.get('pageNumber')} and {len(pageJS.get('products', []))} products")
                                        return {'page': pageJS}
                                    # Если нет на верхнем уровне, проверяем объект 'page'
                                    elif 'page' in pageJS and isinstance(pageJS['page'], dict):
                                        page_obj = pageJS['page']
                                        if 'pageNumber' in page_obj and 'products' in page_obj:
                                            logging.info(f"Found page object inside 'page' key with pageNumber={page_obj.get('pageNumber')} and {len(page_obj.get('products', []))} products")
                                            return {'page': page_obj}
                                        # Если products на верхнем уровне, а pageNumber в page
                                        elif 'pageNumber' in page_obj and 'products' in pageJS:
                                            # Создаем объединенный объект
                                            combined = {**page_obj, 'products': pageJS['products']}
                                            logging.info(f"Found page object (combined) with pageNumber={combined.get('pageNumber')} and {len(combined.get('products', []))} products")
                                            return {'page': combined}
                                    # Если products на верхнем уровне
                                    elif 'products' in pageJS:
                                        # Ищем pageNumber в любом вложенном объекте
                                        if 'page' in pageJS and isinstance(pageJS['page'], dict) and 'pageNumber' in pageJS['page']:
                                            combined = {**pageJS['page'], 'products': pageJS['products']}
                                            logging.info(f"Found page object (combined from nested) with pageNumber={combined.get('pageNumber')} and {len(combined.get('products', []))} products")
                                            return {'page': combined}
                                    else:
                                        logging.info(f"Match {idx+1}: Object contains both fields in text but missing in parsed JSON. Keys: {list(pageJS.keys())[:10]}")
                                except json.JSONDecodeError as e:
                                    # Пробуем следующий объект
                                    continue
                                except Exception as e:
                                    logging.warning(f"Match {idx+1}: Failed to parse page JSON: {e}")
                                    continue
                    
                    logging.info(f"Match {idx+1}: Could not find object containing both pageNumber and products")
            
            logging.info("Object with both pageNumber and products not found in HTML")
        except re.error as e:
            logging.error(f"Regex error: {e}")
        except Exception as e:
            logging.error(f"Error in variant 1: {e}")
        
        # Вариант 2: Старый паттерн (на случай, если где-то еще работает)
        try:
            key = '"pageview",'
            pattern = key + r'\s*(\{.*?\})'
            if pageJS := recjson(pattern, data):
                logging.info("Found data using old pageview pattern")
                return pageJS
        except Exception as e:
            logging.warning(f"Error in old pageview pattern: {e}")
    
    return {}


def listPages(page, sort=None, rooms=None):
    pagesList = []
    response = getResponse(page, type=0, sort=sort, rooms=rooms)
    if not response:
        logging.warning(f"listPages: getResponse returned empty result for page={page}, sort={sort}, rooms={rooms}")
        return []
    pageJS = prePage(response, type=0)
    if not pageJS:
        logging.warning(f"listPages: prePage returned empty result for page={page}, sort={sort}, rooms={rooms}")
        return []
    # pageJS теперь имеет структуру {'page': {...}} или старую структуру
    page_obj = pageJS.get('page', pageJS)  # Поддержка старого и нового формата
    if not page_obj:
        logging.warning(f"listPages: page_obj is empty for page={page}, pageJS keys: {list(pageJS.keys())}")
        return []
    if page_obj.get('pageNumber') != page:
        logging.info(f"Prewiew page {page} is END (pageNumber={page_obj.get('pageNumber')}, requested={page})")
        return 'END'
    if products := page_obj.get('products'):
        for i in products:
            if id := i.get('cianId'):
                logging.info(f"Prewiew page {id} appended")
                pagesList.append(id)
        return pagesList
    logging.info(f"Prewiew page {page} is None")
    return []


def apartPage(pagesList, dbinsert=True, max_retries=2):
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
            
            # Обрабатываем фото отдельно (это массив объектов)
            photos_data = data.pop('photos', [])
            
            if exist:
                instances = [(model, data[key])
                             for key, model in model_classes.items() if key in data]
                for model, update_values in instances:
                    logging.info(f"Apart page {page}, table {model} is updating")
                    DB.update(model, {'cian_id': page}, update_values)
                
                # Для фото: удаляем старые и вставляем новые
                if photos_data:
                    from .database import Photos
                    # Удаляем старые фото для этого объявления
                    session = DB.Session()
                    try:
                        session.query(Photos).filter(Photos.cian_id == page).delete()
                        session.commit()
                    except Exception as e:
                        session.rollback()
                        logging.error(f"Error deleting old photos for {page}: {e}")
                    finally:
                        session.close()
                    
                    # Вставляем новые фото
                    photo_instances = [Photos(**photo) for photo in photos_data]
                    if photo_instances:
                        DB.insert(*photo_instances)
                        logging.info(f"Apart page {page}: added {len(photo_instances)} photos")
            else:
                instances = [model(**data[key])
                             for key, model in model_classes.items() if key in data]
                logging.info(f"Apart page {page} is adding")
                DB.insert(*instances)
                
                # Добавляем фото для нового объявления
                if photos_data:
                    from .database import Photos
                    photo_instances = [Photos(**photo) for photo in photos_data]
                    if photo_instances:
                        DB.insert(*photo_instances)
                        logging.info(f"Apart page {page}: added {len(photo_instances)} photos")
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


