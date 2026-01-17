import logging
import random
import time
import re
import json
from playwright.sync_api import sync_playwright
from .database import DB, model_classes
from .pagecheck import pagecheck
from .tools import headers, proxyDict, proxyBlockedTime, proxyErrorCount, proxyConnectionErrors, proxyTemporaryBan, check_and_unfreeze_proxies, load_proxy_bans, recjson

URL = 'https://www.cian.ru'

_playwright = None
_browser = None

def _get_browser():
    global _playwright, _browser
    if _browser is None or not _browser.is_connected():
        # Если браузер закрыт или не подключен, пересоздаем его
        if _browser:
            try:
                _browser.close()
            except:
                pass
        if _playwright:
            try:
                _playwright.stop()
            except:
                pass
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(headless=True)
        logging.info('Browser recreated')
    return _browser

def close_browser():
    global _playwright, _browser
    if _browser:
        _browser.close()
        _browser = None
    if _playwright:
        _playwright.stop()
        _playwright = None

# Глобальный счетчик CAPTCHA для отслеживания подряд идущих CAPTCHA
_captcha_count = {}  # {page: count}

def getResponse(page, type=0, respTry=5, sort=None, rooms=None, dbinsert=True):
    global _captcha_count
    logging.info(f'getResponse: Starting for page={page}, type={type}, respTry={respTry}, sort={sort}, rooms={rooms}')
    
    if respTry == 5:
        check_and_unfreeze_proxies()
        load_proxy_bans()  # Загружаем актуальные баны из файла
        # Сбрасываем счетчик CAPTCHA для новой страницы
        _captcha_count[page] = 0
    
    # Исключаем пустой прокси и временно забаненные прокси из доступных
    available_proxies = {
        k: v for k, v in proxyDict.items() 
        if v <= time.time() and k != '' and not proxyTemporaryBan.get(k, False)
    }
    
    # Проверяем, не заблокированы ли все прокси CAPTCHA (блокировка > 10 минут)
    # Если да, сразу возвращаем CAPTCHA, чтобы не тратить время
    if len(available_proxies) < 1:
        # Проверяем минимальное время блокировки
        non_empty_proxies = {k: v for k, v in proxyDict.items() if k != ''}
        if non_empty_proxies:
            mintime = min(non_empty_proxies.values())
            current_time = time.time()
            if mintime > current_time:
                block_duration = mintime - current_time
                # Если все прокси заблокированы более чем на 5 минут, вероятно это CAPTCHA
                # Пропускаем страницу сразу, чтобы не тратить время (уменьшено с 10 до 5 минут)
                if block_duration > (5 * 60) and respTry <= 2:
                    logging.warning(f'All proxies blocked for {block_duration/60:.1f} minutes (likely CAPTCHA), skipping page {page}')
                    return 'CAPTCHA'
        
        count = min(len(proxyDict) - 1, 1)
        mintime = sorted(proxyDict.values())[count]
        if (mintime > (timenow := time.time())):
            misstime = min(mintime - timenow, 60)  # Максимум 60 секунд
            logging.info(f'No available proxies, waiting {misstime:.2f} seconds')
            time.sleep(misstime)
            # Исключаем пустой прокси при пересчете
            available_proxies = {k: v for k, v in proxyDict.items() if v <= time.time() and k != ''}
    
    if available_proxies:
        # Улучшенная ротация: выбираем прокси с наименьшим количеством ошибок подключения
        # Это помогает избегать неработающих прокси
        available_proxies_list = list(available_proxies.keys())
        # Сортируем по количеству ошибок подключения (меньше ошибок = лучше)
        available_proxies_list.sort(key=lambda p: proxyConnectionErrors.get(p, 0))
        # Выбираем из прокси с наименьшим количеством ошибок (первые 50% или минимум 1)
        best_proxies = available_proxies_list[:max(1, len(available_proxies_list) // 2)]
        proxy = random.choice(best_proxies)
    else:
        # Если все прокси заблокированы после ожидания
        # НЕ используем пустой прокси - он всегда дает 403, это бессмысленно
        non_empty_proxies = {k: v for k, v in proxyDict.items() if k != ''}
        if non_empty_proxies:
            # Выбираем прокси с наименьшим временем блокировки (освободится раньше всех)
            earliest_proxy = min(non_empty_proxies.items(), key=lambda x: x[1])
            unlock_time = earliest_proxy[1] - time.time()
            # НЕ используем прокси, который заблокирован более чем на 1 минуту
            # Если все прокси заблокированы более чем на 1 минуту, лучше пропустить страницу
            if unlock_time <= 60:  # Если освободится в течение 1 минуты
                proxy = earliest_proxy[0]
                logging.warning(f'All proxies blocked, using earliest available: {proxy[:30]}... (unlocks in {unlock_time:.0f}s)')
            else:
                # Если все прокси заблокированы более чем на 1 минуту, возвращаем CAPTCHA
                if respTry <= 2:
                    logging.warning(f'All proxies blocked for >1 minute (unlock in {unlock_time:.0f}s), skipping page {page}')
                    return 'CAPTCHA'
                # Если есть попытки, ждем освобождения
                wait_time = min(unlock_time, 60)
                logging.warning(f'All proxies blocked for >1 minute, waiting {wait_time:.0f}s before retry')
                time.sleep(wait_time)
                return getResponse(page, type, respTry - 1, sort, rooms, dbinsert)
        else:
            # Нет прокси в словаре вообще - это ошибка конфигурации
            logging.error('No proxies configured in proxyDict')
            return None
    
    # Формируем URL и параметры запроса
    if type == 1:  # Страница объявления
        url = f'{URL}/rent/flat/{page}/'
    else:  # Список страниц (type=0)
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
        # Формируем URL с параметрами
        param_str = '&'.join([f'{k}={v}' for k, v in params.items()])
        url = f'{URL}/cat.php?{param_str}'
    
    logging.info(f'getResponse: URL={url[:100]}..., proxy={proxy[:50] if proxy else "none"}...')
    
    # Делаем запрос через Playwright
    try:
        browser = _get_browser()
        context_options = {}
        
        # Устанавливаем User-Agent
        if headers:
            user_agent = random.choice(headers).get('User-Agent')
            if user_agent:
                context_options['user_agent'] = user_agent
        
        # Устанавливаем прокси с правильной обработкой аутентификации
        if proxy:
            # Если прокси содержит аутентификацию (format: http://USER:PASS@IP:PORT)
            if '@' in proxy:
                from urllib.parse import urlparse
                try:
                    parsed = urlparse(proxy)
                    proxy_server = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
                    context_options['proxy'] = {'server': proxy_server}
                    # Добавляем аутентификацию
                    if parsed.username and parsed.password:
                        context_options['http_credentials'] = {
                            'username': parsed.username,
                            'password': parsed.password
                        }
                except Exception as e:
                    logging.warning(f'Failed to parse proxy {proxy[:50]}...: {e}, using as-is')
                    context_options['proxy'] = {'server': proxy}
            else:
                # Прокси без аутентификации
                context_options['proxy'] = {'server': proxy}
        
        context = None
        page_obj = None
        try:
            context = browser.new_context(**context_options)
            page_obj = context.new_page()
            
            start_time = time.time()
            # Для страниц объявлений используем больший таймаут и более мягкое условие загрузки
            if type == 1:  # Страница объявления
                # Используем 'load' вместо 'domcontentloaded' для более надежной загрузки
                # и увеличиваем таймаут до 90 секунд (прокси могут быть медленными)
                response = page_obj.goto(url, wait_until='load', timeout=90000)
            else:  # Список страниц
                response = page_obj.goto(url, wait_until='networkidle', timeout=30000)
            elapsed = time.time() - start_time
        except Exception as e:
            # Закрываем контекст и страницу при ошибке создания
            if page_obj:
                try:
                    page_obj.close()
                except:
                    pass
            if context:
                try:
                    context.close()
                except:
                    pass
            raise  # Пробрасываем исключение дальше для обработки в основном блоке except
        
        if response:
            status = response.status
            logging.info(f'getResponse: Status={status}, time={elapsed:.2f}s, proxy={proxy[:50] if proxy else "none"}...')
            
            if status != 200:
                logging.error(f'getResponse: Page {page} | Retry: {respTry} | Status: {status}')
                # Безопасное закрытие
                try:
                    if page_obj:
                        page_obj.close()
                except:
                    pass
                try:
                    if context:
                        context.close()
                except:
                    pass
                
                if not respTry:
                    logging.warning(f'getResponse: No retries left, returning None')
                    return None
                
                # Блокируем прокси при ошибках
                if status in (403, 429):
                    # Увеличено время блокировки для более консервативного подхода
                    block_time = 20 * 60  # 20 минут блокировки (увеличено с 10)
                    proxyDict[proxy] = time.time() + block_time
                    proxyErrorCount[proxy] = proxyErrorCount.get(proxy, 0) + 1
                    if proxyErrorCount[proxy] >= 2:
                        proxyBlockedTime[proxy] = time.time()
                        block_time = 30 * 60  # 30 минут при повторных ошибках (увеличено с 15)
                        proxyDict[proxy] = time.time() + block_time
                    logging.warning(f'getResponse: Proxy {proxy[:50]}... blocked for {block_time//60} min (status {status})')
                    # Делаем паузу перед следующей попыткой после 403/429
                    if respTry > 1:
                        delay = random.uniform(10, 20)  # 10-20 секунд пауза
                        logging.info(f'Waiting {delay:.1f}s before retry after {status}')
                        time.sleep(delay)
                elif status == 404:
                    logging.info(f'getResponse: Page {page} not found (404)')
                    return None
                else:
                    proxyDict[proxy] = time.time() + (1 * 60)  # 1 минута блокировки
                
                return getResponse(page, type, respTry - 1, sort, rooms, dbinsert)
            
            # Успешный запрос
            content = page_obj.content()
            # Безопасное закрытие
            try:
                if page_obj:
                    page_obj.close()
            except:
                pass
            try:
                if context:
                    context.close()
            except:
                pass
            
            # Проверяем на CAPTCHA в содержимом (до парсинга)
            if content and ('captcha' in content.lower() or 'капча' in content.lower() or 'recaptcha' in content.lower()):
                logging.error("CAPTCHA detected in response content!")
                if proxy:
                    logging.warning(f"Blocking proxy {proxy[:50]}... for 60 minutes due to CAPTCHA")
                    proxyDict[proxy] = time.time() + (60 * 60)  # 60 минут блокировки (увеличено с 30)
                    proxyBlockedTime[proxy] = time.time()
                    proxyErrorCount[proxy] = proxyErrorCount.get(proxy, 0) + 1
                
                # Увеличиваем счетчик CAPTCHA для этой страницы
                _captcha_count[page] = _captcha_count.get(page, 0) + 1
                
                # Если 2 или более прокси подряд получили CAPTCHA, делаем длительную паузу и пропускаем страницу
                if _captcha_count[page] >= 2:
                    logging.warning(f'{_captcha_count[page]} CAPTCHA in a row for page {page}, waiting 2 minutes before skipping')
                    time.sleep(120)  # 2 минуты пауза после множественных CAPTCHA
                    return 'CAPTCHA'
                
                # Если осталось мало попыток и все прокси заблокированы, делаем паузу и возвращаем CAPTCHA
                if respTry <= 2:
                    # Проверяем, сколько прокси доступно
                    available_after_captcha = {k: v for k, v in proxyDict.items() if v <= time.time() and k != ''}
                    if len(available_after_captcha) == 0:
                        logging.warning(f'All proxies blocked after CAPTCHA, waiting 1 minute before skipping page {page}')
                        time.sleep(60)  # 1 минута пауза
                        return 'CAPTCHA'
                
                # Делаем паузу перед следующей попыткой после CAPTCHA
                if respTry > 1:
                    delay = random.uniform(30, 60)  # 30-60 секунд пауза
                    logging.info(f'Waiting {delay:.1f}s before retry after CAPTCHA')
                    time.sleep(delay)
                
                if not respTry:
                    return 'CAPTCHA'
                return getResponse(page, type, respTry - 1, sort, rooms, dbinsert)
            
            # Обновляем время блокировки прокси после успешного запроса
            # Блокируем прокси на 2 минуты после успешного запроса, чтобы дать ему "отдохнуть"
            # Это снижает вероятность CAPTCHA при повторном использовании
            proxyDict[proxy] = time.time() + (2 * 60)  # 2 минуты блокировки прокси после успешного запроса
            proxyErrorCount[proxy] = 0  # Сбрасываем счетчик ошибок
            # Сбрасываем счетчик ошибок подключения при успешном запросе (прокси работает!)
            proxyConnectionErrors[proxy] = 0
            # Сбрасываем счетчик CAPTCHA при успешном запросе
            if page in _captcha_count:
                _captcha_count[page] = 0
            
            # Добавляем случайную задержку между запросами (5-15 секунд)
            # Это помогает избежать детекции автоматизации
            delay = random.uniform(5, 15)
            logging.info(f'getResponse: Success, content length={len(content)}, waiting {delay:.1f}s before next request')
            time.sleep(delay)
            
            logging.info(f'getResponse: Success, content length={len(content)}')
            return content
        else:
            logging.error(f'getResponse: No response received')
            # Безопасное закрытие
            try:
                if page_obj:
                    page_obj.close()
            except:
                pass
            try:
                if context:
                    context.close()
            except:
                pass
            
            if not respTry:
                return None
            
            proxyDict[proxy] = time.time() + (1 * 60)
            return getResponse(page, type, respTry - 1, sort, rooms, dbinsert)
            
    except Exception as e:
        error_msg = str(e)
        logging.error(f'getResponse: Exception for proxy {proxy[:50] if proxy else "none"}...: {e}')
        
        # Если браузер закрыт, пересоздаем его
        if 'closed' in error_msg.lower() or 'has been closed' in error_msg.lower():
            logging.warning('Browser/context/page was closed, recreating browser')
            try:
                close_browser()
            except:
                pass
            # Принудительно сбрасываем браузер
            global _browser, _playwright
            _browser = None
            _playwright = None
        
        if not respTry:
            logging.warning(f'getResponse: No retries left after exception, returning None')
            return None
        
        # Блокируем прокси при исключении
        if proxy:
            # Проверяем, является ли это ошибкой подключения
            if 'connection' in error_msg.lower() or 'err_proxy' in error_msg.lower():
                # Ошибка подключения - блокируем на более длительное время
                proxyConnectionErrors[proxy] = proxyConnectionErrors.get(proxy, 0) + 1
                connection_errors = proxyConnectionErrors[proxy]
                
                # Если много ошибок подключения подряд, блокируем на долго
                if connection_errors >= 3:
                    block_time = 60 * 60  # 1 час блокировки
                    logging.warning(f'Proxy {proxy[:50]}... has {connection_errors} connection errors, blocking for 1 hour')
                elif connection_errors >= 2:
                    block_time = 30 * 60  # 30 минут блокировки
                    logging.warning(f'Proxy {proxy[:50]}... has {connection_errors} connection errors, blocking for 30 min')
                else:
                    block_time = 10 * 60  # 10 минут блокировки
                    logging.warning(f'Proxy {proxy[:50]}... connection error, blocking for 10 min')
                
                proxyDict[proxy] = time.time() + block_time
                proxyBlockedTime[proxy] = time.time()
            else:
                # Другая ошибка - обычная блокировка
                proxyDict[proxy] = time.time() + (1 * 60)
            proxyErrorCount[proxy] = proxyErrorCount.get(proxy, 0) + 1
        
        return getResponse(page, type, respTry - 1, sort, rooms, dbinsert)
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
                # Сохраняем часть HTML для анализа (первые 2000 символов и последние 2000)
                preview_start = data[:2000] if len(data) > 2000 else data
                preview_end = data[-2000:] if len(data) > 2000 else ""
                logging.warning(f"HTML preview (first 2000 chars): {preview_start}")
                if preview_end:
                    logging.warning(f"HTML preview (last 2000 chars): {preview_end}")
                
                # Проверяем, не блокировка ли это (капча, 403 и т.д.)
                captcha_detected = False
                if 'captcha' in data.lower() or 'капча' in data.lower() or 'recaptcha' in data.lower():
                    logging.error("CAPTCHA detected in response!")
                    captcha_detected = True
                if 'blocked' in data.lower() or 'заблокирован' in data.lower():
                    logging.error("Blocked response detected!")
                if 'access denied' in data.lower() or 'доступ запрещен' in data.lower():
                    logging.error("Access denied in response!")
                
                # Если обнаружена CAPTCHA, блокируем прокси на 30 минут и возвращаем специальное значение
                if captcha_detected and proxy:
                    logging.warning(f"Blocking proxy {proxy[:50]}... for 30 minutes due to CAPTCHA")
                    proxyDict[proxy] = time.time() + (30 * 60)  # 30 минут блокировки
                    proxyBlockedTime[proxy] = time.time()
                    proxyErrorCount[proxy] = proxyErrorCount.get(proxy, 0) + 1
                    return 'CAPTCHA'
            
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
    logging.info(f"listPages: Starting for page={page}, sort={sort}, rooms={rooms}")
    pagesList = []
    response = getResponse(page, type=0, sort=sort, rooms=rooms)
    
    # Обработка CAPTCHA - пропускаем страницу и возвращаем пустой список
    # чтобы парсер мог продолжить со следующей страницы
    if response == 'CAPTCHA':
        logging.warning(f"listPages: CAPTCHA detected for page={page}, sort={sort}, rooms={rooms}, skipping page")
        return []  # Возвращаем пустой список, чтобы парсер продолжил
    
    if not response:
        logging.warning(f"listPages: getResponse returned None for page={page}, sort={sort}, rooms={rooms}")
        return []
    
    pageJS = prePage(response, type=0)
    if not pageJS:
        logging.warning(f"listPages: prePage returned None for page={page}, sort={sort}, rooms={rooms}")
        return []
    
    page_obj = pageJS.get('page', pageJS)
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


def apartPage(pagesList, dbinsert=True, max_retries=2):
    """
    Парсит список объявлений с улучшенной логикой пропуска проблемных.
    max_retries - максимальное количество попыток для одного объявления
    """
    pages_cnt = 0
    skipped_count = 0
    existing_count = 0
    filtered_count = 0
    failed_pages = {}  # Счетчик неудачных попыток для каждого объявления
    
    for page in pagesList:
        exist = False
        if dbinsert and DB.select(model_classes['offers'], filter_by={'cian_id': page}):
            exist = True
            existing_count += 1
            logging.info(f"Apart page {page} already exists")
            continue
        
        # Проверяем, сколько раз мы уже пытались парсить это объявление
        retry_count = failed_pages.get(page, 0)
        if retry_count >= max_retries:
            skipped_count += 1
            logging.info(f"Apart page {page} skipped after {retry_count} failed attempts")
            continue
        
        response = getResponse(page, type=1, dbinsert=dbinsert, respTry=2)  # Уменьшено до 2 попыток для быстрей обработки
        
        # Обработка CAPTCHA - пропускаем объявление
        if response == 'CAPTCHA':
            logging.warning(f"Apart page {page}: CAPTCHA detected, skipping")
            filtered_count += 1  # Считаем как отфильтрованное
            continue
        
        if not response:
            failed_pages[page] = retry_count + 1
            if retry_count + 1 < max_retries:
                logging.info(f"Apart page {page} failed, will retry later (attempt {retry_count + 1}/{max_retries})")
            continue
        
        pageJS = prePage(response, type=1)
        if data := pagecheck(pageJS):
            # Обрабатываем фото отдельно (это массив объектов)
            photos_data = data.pop('photos', [])
            if not dbinsert:
                return data
            if exist:
                # Это не должно произойти, т.к. exist проверяется выше
                existing_count += 1
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
            # pagecheck вернул None - объявление отфильтровано (deal_type != 'rent' или category == 'dailyFlatRent')
            filtered_count += 1
            failed_pages[page] = retry_count + 1
            if retry_count + 1 < max_retries:
                logging.info(f"Apart page {page} parse failed, will retry later (attempt {retry_count + 1}/{max_retries})")
        continue
    
    logging.info(f"Apart pages {pagesList[:5]}{'...' if len(pagesList) > 5 else ''} processed. Added: {pages_cnt}, Existing: {existing_count}, Filtered: {filtered_count}, Skipped: {skipped_count}")
    
    # Если были добавлены новые объявления, возвращаем 'OK'
    if pages_cnt > 0:
        logging.info(f"SUCCESS: Added {pages_cnt} new offers from {len(pagesList)} total")
        return 'OK'
    
    # Если все объявления уже в базе, возвращаем 'EXISTING'
    if existing_count > 0 and pages_cnt == 0 and filtered_count == 0:
        logging.info(f"All {existing_count} offers already exist in database")
        return 'EXISTING'
    
    # Если все объявления отфильтрованы, возвращаем 'FILTERED'
    if filtered_count > 0 and pages_cnt == 0:
        logging.info(f"All {filtered_count} offers were filtered out")
        return 'FILTERED'
    
    # Если все объявления пропущены (CAPTCHA/ошибки), возвращаем 'SKIPPED'
    if skipped_count > 0 and pages_cnt == 0:
        logging.warning(f"All {skipped_count} offers were skipped due to errors/CAPTCHA")
        return 'SKIPPED'
    
    # Если список был пуст или ничего не обработано
    if len(pagesList) == 0:
        logging.warning("Empty pagesList passed to apartPage")
        return None
    
    # По умолчанию возвращаем 'OK' для обработанных страниц
    return 'OK'


