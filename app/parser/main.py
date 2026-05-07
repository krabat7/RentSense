import logging
import random
import time
import re
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright
from .database import DB, model_classes
from .pagecheck import pagecheck
from .tools import headers, proxyDict, proxyBlockedTime, proxyErrorCount, proxyConnectionErrors, proxyTemporaryBan, check_and_unfreeze_proxies, load_proxy_bans, recjson

# curl_cffi: HTTP с имитацией TLS (резидентские прокси).
try:
    import curl_cffi.requests as curl_requests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False
    logging.warning("curl_cffi not available, will use Playwright only")

URL = 'https://www.cian.ru'


def fetch_flat_page_html_http(flat_id: str, timeout: float = 20.0) -> str | None:
    """GET страницы объявления; в HTML ищется вложенный JSON offerData."""
    import httpx

    url = f"{URL}/rent/flat/{flat_id}/"
    hdrs = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.cian.ru/",
    }
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            r = client.get(url, headers=hdrs)
        if r.status_code != 200:
            logging.info(
                "fetch_flat_page_html_http: status %s for flat_id=%s", r.status_code, flat_id
            )
            return None
        text = r.text
        if '"offerData"' not in text:
            logging.info("fetch_flat_page_html_http: no offerData, flat_id=%s", flat_id)
            return None
        low = text.lower()
        if "tmgrdfrend/showcaptcha" in low or "showcaptcha" in low:
            logging.info("fetch_flat_page_html_http: captcha page, flat_id=%s", flat_id)
            return None
        return text
    except Exception as e:
        logging.warning("fetch_flat_page_html_http: flat_id=%s err=%s", flat_id, e)
        return None


def fetch_flat_page_curl_cffi_direct(flat_id: str, timeout: float = 25.0) -> str | None:
    """GET через curl_cffi с impersonate=chrome110."""
    if not CURL_CFFI_AVAILABLE:
        return None
    url = f"{URL}/rent/flat/{flat_id}/"
    hdrs = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.cian.ru/",
    }
    try:
        r = curl_requests.get(url, headers=hdrs, timeout=timeout, impersonate="chrome110")
        if r.status_code != 200:
            logging.info(
                "fetch_flat_page_curl_cffi_direct: status %s flat_id=%s",
                r.status_code,
                flat_id,
            )
            return None
        text = r.text
        if '"offerData"' not in text:
            return None
        if "tmgrdfrend/showcaptcha" in text.lower():
            return None
        return text
    except Exception as e:
        logging.warning("fetch_flat_page_curl_cffi_direct: flat_id=%s %s", flat_id, e)
        return None


_playwright = None
_browser = None

def _get_browser():
    global _playwright, _browser
    if _browser is None or not _browser.is_connected():
        # Пересоздание Chromium при обрыве соединения.
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
        # Headless Chromium: снижение признаков automation.
        _browser = _playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
            ]
        )
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

# Число подряд CAPTCHA на одном page (ключ: номер страницы списка или id объявления).
_captcha_count = {}

def getResponse(page, type=0, respTry=5, sort=None, rooms=None, dbinsert=True, use_proxy=True):
    global _captcha_count
    logging.info(f'getResponse: Starting for page={page}, type={type}, respTry={respTry}, use_proxy={use_proxy}')
    
    proxy = None
    if use_proxy:
        if respTry == 5:
            check_and_unfreeze_proxies()
            load_proxy_bans()
            # Новый цикл запросов к этому page, обнулить счетчик CAPTCHA.
            _captcha_count[page] = 0

        # Доступны прокси без пустого ключа, не в temporary ban и с истёкшим blocked_until.
        available_proxies = {
            k: v for k, v in proxyDict.items()
            if v <= time.time() and k != '' and not proxyTemporaryBan.get(k, False)
        }

        # Сводка по прокси при первой попытке (respTry == начальное значение).
        if respTry == 5:
            total_proxies = len([p for p in proxyDict.keys() if p != ''])
            banned_proxies = sum(1 for p in proxyDict.keys() if p != '' and proxyTemporaryBan.get(p, False))
            time_blocked = sum(1 for k, v in proxyDict.items() if k != '' and v > time.time() and not proxyTemporaryBan.get(k, False))
            available_count = len(available_proxies)
            new_proxies_available = sum(1 for p in available_proxies.keys() if '4MfBTo:mgCBFh' in p)
            logging.info(f'Proxy stats: total={total_proxies}, banned={banned_proxies}, time_blocked={time_blocked}, available={available_count}, new_proxies_available={new_proxies_available}')

        # Все прокси заняты: при длительной блокировке и малом respTry вернуть CAPTCHA.
        if len(available_proxies) < 1:
            non_empty_proxies = {k: v for k, v in proxyDict.items() if k != ''}
            if non_empty_proxies:
                mintime = min(non_empty_proxies.values())
                current_time = time.time()
                if mintime > current_time:
                    block_duration = mintime - current_time
                    if block_duration > (5 * 60) and respTry <= 2:
                        logging.warning(f'All proxies blocked for {block_duration/60:.1f} minutes (likely CAPTCHA), skipping page {page}')
                        return 'CAPTCHA'

                count = min(len(proxyDict) - 1, 1)
                mintime = sorted(proxyDict.values())[count]
                if (mintime > (timenow := time.time())):
                    misstime = min(mintime - timenow, 60)
                    logging.info(f'No available proxies, waiting {misstime:.2f} seconds')
                    time.sleep(misstime)
                    available_proxies = {k: v for k, v in proxyDict.items() if v <= time.time() and k != ''}

        if available_proxies:
            available_proxies_list = list(available_proxies.keys())
            available_proxies_list.sort(key=lambda p: proxyConnectionErrors.get(p, 0))
            best_proxies = available_proxies_list[:max(1, len(available_proxies_list) // 2)]
            proxy = random.choice(best_proxies)
            if respTry == 5:
                new_proxies = [p for p in best_proxies if '4MfBTo:mgCBFh' in p]
                errors_list = [proxyConnectionErrors.get(p, 0) for p in best_proxies[:5]]
                if new_proxies:
                    logging.info(f'Selected proxy from {len(best_proxies)} best proxies (errors: {errors_list}), new proxies in pool: {len(new_proxies)}')
                else:
                    new_in_available = [p for p in available_proxies.keys() if '4MfBTo:mgCBFh' in p]
                    if new_in_available:
                        new_errors = [proxyConnectionErrors.get(p, 0) for p in new_in_available]
                        logging.warning(f'Selected proxy from {len(best_proxies)} best proxies (errors: {errors_list}), new proxies NOT in best pool (have {len(new_in_available)} new with errors: {new_errors})')
                    else:
                        logging.info(f'Selected proxy from {len(best_proxies)} best proxies (errors: {errors_list}), no new proxies available')
        else:
            non_empty_proxies = {k: v for k, v in proxyDict.items() if k != ''}
            if non_empty_proxies:
                earliest_proxy = min(non_empty_proxies.items(), key=lambda x: x[1])
                unlock_time = earliest_proxy[1] - time.time()
                if unlock_time <= 60:
                    proxy = earliest_proxy[0]
                    logging.warning(f'All proxies blocked, using earliest available: {proxy[:30]}... (unlocks in {unlock_time:.0f}s)')
                else:
                    if respTry <= 2:
                        logging.warning(f'All proxies blocked for >1 minute (unlock in {unlock_time:.0f}s), skipping page {page}')
                        return 'CAPTCHA'
                    wait_time = min(unlock_time, 60)
                    logging.warning(f'All proxies blocked for >1 minute, waiting {wait_time:.0f}s before retry')
                    time.sleep(wait_time)
                    return getResponse(page, type, respTry - 1, sort, rooms, dbinsert, use_proxy)
            else:
                logging.error('No proxies configured in proxyDict')
                return None

    # URL: карточка объявления (type=1) или cat.php со списком (type=0).
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
        # Query string для выдачи списка.
        param_str = '&'.join([f'{k}={v}' for k, v in params.items()])
        url = f'{URL}/cat.php?{param_str}'
    
    logging.info(f'getResponse: URL={url[:100]}..., proxy={proxy[:50] if proxy else "none"}...')
    
    # Поддомен pool.proxy.market: запрос через curl_cffi, не через Playwright.
    if proxy and 'pool.proxy.market' in proxy and CURL_CFFI_AVAILABLE:
        try:
            logging.info(f'Using curl_cffi for residential proxy')
            start_time = time.time()
            
            # Словарь proxies для curl_cffi.
            proxies = {"http": proxy, "https": proxy}
            
            # Случайный набор из tools.headers.
            if headers:
                selected_headers = random.choice(headers).copy()
            else:
                selected_headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Referer": "https://www.cian.ru/",
                }
            
            # GET с TLS-имперсонацией.
            response = curl_requests.get(
                url,
                headers=selected_headers,
                proxies=proxies,
                timeout=30,
                impersonate="chrome110"
            )
            
            elapsed = time.time() - start_time
            status = response.status_code
            content = response.text
            
            logging.info(f'getResponse (curl_cffi): Status={status}, time={elapsed:.2f}s, proxy={proxy[:50]}...')
            
            if status != 200:
                logging.error(f'getResponse (curl_cffi): Page {page} | Retry: {respTry} | Status: {status}')
                
                if not respTry:
                    logging.warning(f'getResponse (curl_cffi): No retries left, returning None')
                    return None
                
                # Ошибка ответа: увеличить blocked_until у прокси.
                if status in (403, 429):
                    block_time = 20 * 60
                    proxyDict[proxy] = time.time() + block_time
                    proxyErrorCount[proxy] = proxyErrorCount.get(proxy, 0) + 1
                    if proxyErrorCount[proxy] >= 2:
                        proxyBlockedTime[proxy] = time.time()
                        block_time = 30 * 60
                        proxyDict[proxy] = time.time() + block_time
                    logging.warning(f'getResponse (curl_cffi): Proxy {proxy[:50]}... blocked for {block_time//60} min (status {status})')
                    if respTry > 1:
                        delay = random.uniform(10, 20)
                        logging.info(f'Waiting {delay:.1f}s before retry after {status}')
                        time.sleep(delay)
                elif status == 404:
                    logging.info(f'getResponse (curl_cffi): Page {page} not found (404)')
                    return None
                else:
                    proxyDict[proxy] = time.time() + (1 * 60)
                
                return getResponse(page, type, respTry - 1, sort, rooms, dbinsert, use_proxy)
            
            # Текст ответа: признаки CAPTCHA.
            if content and ('captcha' in content.lower() or 'капча' in content.lower() or 'recaptcha' in content.lower()):
                logging.error("CAPTCHA detected in response content (curl_cffi)!")
                if proxy:
                    proxyErrorCount[proxy] = proxyErrorCount.get(proxy, 0) + 1
                    if proxyErrorCount[proxy] >= 2:
                        block_time = 15 * 60
                    else:
                        block_time = 10 * 60
                    proxyDict[proxy] = time.time() + block_time
                    proxyBlockedTime[proxy] = time.time()
                    logging.warning(f"Blocking proxy {proxy[:50]}... for {block_time//60} min due to CAPTCHA (errors: {proxyErrorCount[proxy]})")
                
                _captcha_count[page] = _captcha_count.get(page, 0) + 1
                
                if _captcha_count[page] >= 2:
                    logging.warning(f'{_captcha_count[page]} CAPTCHA in a row for page {page}, waiting 2 minutes before skipping')
                    time.sleep(120)
                    return 'CAPTCHA'
                
                if respTry <= 2:
                    available_after_captcha = {k: v for k, v in proxyDict.items() if v <= time.time() and k != ''}
                    if len(available_after_captcha) == 0:
                        logging.warning(f'All proxies blocked after CAPTCHA, waiting 1 minute before skipping page {page}')
                        time.sleep(60)
                        return 'CAPTCHA'
                
                if respTry > 1:
                    delay = random.uniform(30, 60)
                    logging.info(f'Waiting {delay:.1f}s before retry after CAPTCHA')
                    time.sleep(delay)
                
                if not respTry:
                    return 'CAPTCHA'
                return getResponse(page, type, respTry - 1, sort, rooms, dbinsert, use_proxy)
            
            # Успех curl_cffi: сброс ошибок по прокси.
            proxyDict[proxy] = time.time() + 0
            proxyErrorCount[proxy] = 0
            proxyConnectionErrors[proxy] = 0
            if page in _captcha_count:
                _captcha_count[page] = 0
            
            # Случайная пауза между запросами только при записи в БД (фоновый парсер).
            if dbinsert:
                if random.random() < 0.7:
                    delay = random.uniform(3, 12)
                else:
                    delay = random.uniform(12, 25)
                logging.info(
                    f"getResponse (curl_cffi): Success, len={len(content)}, wait {delay:.1f}s (batch)"
                )
                time.sleep(delay)

            logging.info(f'getResponse (curl_cffi): Success, content length={len(content)}')
            return content
            
        except Exception as e:
            error_msg = str(e)
            logging.error(f'getResponse (curl_cffi): Exception for proxy {proxy[:50] if proxy else "none"}...: {e}')
            
            if not respTry:
                logging.warning(f'getResponse (curl_cffi): No retries left after exception, returning None')
                return None
            
            # Исключение curl_cffi: блокировка прокси по типу ошибки.
            if proxy:
                if 'connection' in error_msg.lower() or 'timeout' in error_msg.lower():
                    proxyConnectionErrors[proxy] = proxyConnectionErrors.get(proxy, 0) + 1
                    connection_errors = proxyConnectionErrors[proxy]
                    
                    if connection_errors >= 3:
                        block_time = 60 * 60
                        logging.warning(f'Proxy {proxy[:50]}... has {connection_errors} connection errors, blocking for 1 hour')
                    elif connection_errors >= 2:
                        block_time = 30 * 60
                        logging.warning(f'Proxy {proxy[:50]}... has {connection_errors} connection errors, blocking for 30 min')
                    else:
                        block_time = 10 * 60
                        logging.warning(f'Proxy {proxy[:50]}... connection error, blocking for 10 min')
                    
                    proxyDict[proxy] = time.time() + block_time
                    proxyBlockedTime[proxy] = time.time()
                else:
                    proxyDict[proxy] = time.time() + (1 * 60)
                proxyErrorCount[proxy] = proxyErrorCount.get(proxy, 0) + 1
            
            return getResponse(page, type, respTry - 1, sort, rooms, dbinsert, use_proxy)
    
    # Остальные прокси или прямой заход: Playwright.
    try:
        browser = _get_browser()
        context_options = {}
        
        # user_agent и extra_http_headers из случайного элемента tools.headers.
        if headers:
            selected_headers = random.choice(headers)
            context_options['user_agent'] = selected_headers.get('User-Agent')
            extra_headers = {k: v for k, v in selected_headers.items() if k != 'User-Agent'}
            if extra_headers:
                context_options['extra_http_headers'] = extra_headers
        
        # Параметры контекста: viewport, locale, geolocation Москвы.
        context_options['viewport'] = {'width': 1920, 'height': 1080}
        context_options['locale'] = 'ru-RU'
        context_options['timezone_id'] = 'Europe/Moscow'
        context_options['geolocation'] = {'latitude': 55.7558, 'longitude': 37.6173}  # Москва
        context_options['permissions'] = ['geolocation']
        context_options['color_scheme'] = 'light'
        context_options['device_scale_factor'] = 1
        context_options['has_touch'] = False
        context_options['is_mobile'] = False
        context_options['java_script_enabled'] = True
        
        # proxy в контексте: разбор userinfo из URL при необходимости.
        if proxy:
            # URL вида http://user:pass@host:port: server + http_credentials.
            if '@' in proxy:
                from urllib.parse import urlparse
                try:
                    parsed = urlparse(proxy)
                    proxy_server = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
                    context_options['proxy'] = {'server': proxy_server}
                    if parsed.username and parsed.password:
                        context_options['http_credentials'] = {
                            'username': parsed.username,
                            'password': parsed.password
                        }
                except Exception as e:
                    logging.warning(f'Failed to parse proxy {proxy[:50]}...: {e}, using as-is')
                    context_options['proxy'] = {'server': proxy}
            else:
                context_options['proxy'] = {'server': proxy}
        
        context = None
        page_obj = None
        try:
            context = browser.new_context(**context_options)
            
            # init_script: маскировка navigator.webdriver и связанных полей.
            context.add_init_script("""
                // Убираем webdriver
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Подменяем chrome
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };
                
                // Подменяем plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // Подменяем languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ru-RU', 'ru', 'en-US', 'en']
                });
                
                // Подменяем permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
            
            page_obj = context.new_page()
            
            start_time = time.time()
            # wait_until=domcontentloaded, timeout 30 s.
            response = page_obj.goto(url, wait_until='domcontentloaded', timeout=30000)
            elapsed = time.time() - start_time
        except Exception as e:
            # Закрыть page/context при сбое goto.
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
            raise
        
        if response:
            status = response.status
            logging.info(f'getResponse: Status={status}, time={elapsed:.2f}s, proxy={proxy[:50] if proxy else "none"}...')
            
            if status != 200:
                logging.error(f'getResponse: Page {page} | Retry: {respTry} | Status: {status}')
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

                if proxy:
                    if status in (403, 429):
                        block_time = 15 * 60
                        proxyDict[proxy] = time.time() + block_time
                        proxyErrorCount[proxy] = proxyErrorCount.get(proxy, 0) + 1
                        if proxyErrorCount[proxy] >= 2:
                            proxyBlockedTime[proxy] = time.time()
                            block_time = 20 * 60
                            proxyDict[proxy] = time.time() + block_time
                        logging.warning(f'getResponse: Proxy {proxy[:50]}... blocked for {block_time//60} min (status {status})')
                        if respTry > 1:
                            delay = random.uniform(10, 20)
                            logging.info(f'Waiting {delay:.1f}s before retry after {status}')
                            time.sleep(delay)
                    elif status != 404:
                        proxyDict[proxy] = time.time() + (1 * 60)
                elif status in (403, 429):
                    # Первый заход без прокси: повтор с прокси.
                    if not use_proxy and respTry > 0:
                        logging.info(f'getResponse: Status {status} without proxy, retrying with proxy')
                        return getResponse(page, type, respTry - 1, sort, rooms, dbinsert, use_proxy=True)
                    logging.warning(f'getResponse: Status {status} without proxy, returning None')
                    return None

                if status == 404:
                    logging.info(f'getResponse: Page {page} not found (404)')
                    return None

                return getResponse(page, type, respTry - 1, sort, rooms, dbinsert, use_proxy)
            
            # HTTP 200: далее детект CAPTCHA до закрытия page.
            current_url = page_obj.url
            
            is_captcha_redirect = 'captcha' in current_url.lower() or 'showcaptcha' in current_url.lower()
            
            captcha_visible = False
            try:
                captcha_selectors = [
                    'iframe[src*="captcha"]',
                    'iframe[src*="recaptcha"]',
                    '.captcha:visible',
                    '#captcha:visible',
                ]
                for selector in captcha_selectors:
                    try:
                        elem = page_obj.query_selector(selector)
                        if elem and elem.is_visible():
                            captcha_visible = True
                            break
                    except:
                        continue
            except:
                pass
            
            # type==1: одна карточка, без обхода списка и без inner_text('body').
            single_offer = (type == 1)
            has_content = False
            visible_text = ""
            has_vpn_message = False
            cards_count = 0
            if single_offer:
                has_content = True
            else:
                try:
                    content_selectors = [
                        '[data-name="CardComponent"]', '.c6e8ba5398', 'article',
                        '[data-testid="card"]', '.catalog-serp',
                    ]
                    for selector in content_selectors:
                        try:
                            if page_obj.query_selector(selector):
                                has_content = True
                                break
                        except:
                            continue
                except:
                    pass
                try:
                    visible_text = page_obj.inner_text('body').lower()
                    vpn_patterns = [
                        'кажется, у вас включён vpn', 'отключите его и обновите страницу',
                        'waf_block', 'cian_waf_block',
                    ]
                    has_vpn_message = any(p in visible_text for p in vpn_patterns)
                except:
                    pass
                if has_content:
                    try:
                        cards = page_obj.query_selector_all('[data-name="CardComponent"], .c6e8ba5398, article')
                        cards_count = len(cards)
                    except:
                        pass

            content = page_obj.content()
            
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
            
            captcha_detected = False
            if is_captcha_redirect:
                logging.error("CAPTCHA detected: redirect to CAPTCHA page!")
                captcha_detected = True
            elif captcha_visible:
                logging.error("CAPTCHA detected: visible CAPTCHA element on page!")
                captcha_detected = True
            elif has_vpn_message and not has_content:
                logging.error("CAPTCHA detected: VPN block message (no content found)!")
                captcha_detected = True
            elif content and ('showcaptcha' in content.lower() or 'tmgrdfrend/showcaptcha' in content.lower()):
                logging.error("CAPTCHA detected: CAPTCHA redirect pattern in content!")
                captcha_detected = True
            
            if has_content and not is_captcha_redirect and not captcha_visible:
                logging.info(f"Content found on page - page is working (found {cards_count} cards/items)")
                captcha_detected = False
            
            if captcha_detected:
                if proxy:
                    proxyErrorCount[proxy] = proxyErrorCount.get(proxy, 0) + 1
                    if proxyErrorCount[proxy] >= 2:
                        block_time = 15 * 60
                    else:
                        block_time = 10 * 60
                    proxyDict[proxy] = time.time() + block_time
                    proxyBlockedTime[proxy] = time.time()
                    logging.warning(f"Blocking proxy {proxy[:50]}... for {block_time//60} min due to CAPTCHA (errors: {proxyErrorCount[proxy]})")
                
                _captcha_count[page] = _captcha_count.get(page, 0) + 1
                
                if _captcha_count[page] >= 2:
                    logging.warning(f'{_captcha_count[page]} CAPTCHA in a row for page {page}, waiting 2 minutes before skipping')
                    time.sleep(120)
                    return 'CAPTCHA'
                
                if respTry <= 2:
                    available_after_captcha = {k: v for k, v in proxyDict.items() if v <= time.time() and k != ''}
                    if len(available_after_captcha) == 0:
                        logging.warning(f'All proxies blocked after CAPTCHA, waiting 1 minute before skipping page {page}')
                        time.sleep(60)
                        return 'CAPTCHA'
                
                if respTry > 1:
                    delay = random.uniform(30, 60)
                    logging.info(f'Waiting {delay:.1f}s before retry after CAPTCHA')
                    time.sleep(delay)
                
                if not respTry:
                    return 'CAPTCHA'
                return getResponse(page, type, respTry - 1, sort, rooms, dbinsert, use_proxy)
            
            if proxy:
                proxyDict[proxy] = time.time() + 0
                proxyErrorCount[proxy] = 0
                proxyConnectionErrors[proxy] = 0
            if page in _captcha_count:
                _captcha_count[page] = 0
            
            if single_offer or not dbinsert:
                delay = 0
            else:
                if random.random() < 0.7:
                    delay = random.uniform(3, 12)
                else:
                    delay = random.uniform(12, 28)
            if delay > 0:
                logging.info(f'getResponse: Success, content length={len(content)}, waiting {delay:.1f}s before next request')
                time.sleep(delay)
            
            logging.info(f'getResponse: Success, content length={len(content)}')
            return content
        else:
            logging.error(f'getResponse: No response received')
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

            if proxy:
                proxyDict[proxy] = time.time() + (1 * 60)
            return getResponse(page, type, respTry - 1, sort, rooms, dbinsert, use_proxy)

    except Exception as e:
        error_msg = str(e)
        logging.error(f'getResponse: Exception for proxy {proxy[:50] if proxy else "none"}...: {e}')
        
        if 'closed' in error_msg.lower() or 'has been closed' in error_msg.lower():
            logging.warning('Browser/context/page was closed, recreating browser')
            try:
                close_browser()
            except:
                pass
            global _browser, _playwright
            _browser = None
            _playwright = None
        
        if not respTry:
            logging.warning(f'getResponse: No retries left after exception, returning None')
            return None
        
        if proxy:
            if 'connection' in error_msg.lower() or 'err_proxy' in error_msg.lower():
                proxyConnectionErrors[proxy] = proxyConnectionErrors.get(proxy, 0) + 1
                connection_errors = proxyConnectionErrors[proxy]
                
                if connection_errors >= 3:
                    block_time = 60 * 60
                    logging.warning(f'Proxy {proxy[:50]}... has {connection_errors} connection errors, blocking for 1 hour')
                elif connection_errors >= 2:
                    block_time = 30 * 60
                    logging.warning(f'Proxy {proxy[:50]}... has {connection_errors} connection errors, blocking for 30 min')
                else:
                    block_time = 10 * 60
                    logging.warning(f'Proxy {proxy[:50]}... connection error, blocking for 10 min')
                
                proxyDict[proxy] = time.time() + block_time
                proxyBlockedTime[proxy] = time.time()
            else:
                proxyDict[proxy] = time.time() + (1 * 60)
            proxyErrorCount[proxy] = proxyErrorCount.get(proxy, 0) + 1
        
        return getResponse(page, type, respTry - 1, sort, rooms, dbinsert, use_proxy)
def prePage(data, type=0, proxy=None):
    if type:
        # Карточка: JSON после ключа offerData.
        key = '"offerData":'
        pattern = key + r'\s*(\{.*?\})'
        if pageJS := recjson(pattern, data):
            return pageJS
    else:
        # Список выдачи: объект с pageNumber и products (скобочный разбор по вхождениям в HTML).
        try:
            has_pageNumber = '"pageNumber"' in data
            has_products = '"products"' in data
            logging.info(f"HTML check: pageNumber={has_pageNumber}, products={has_products}, HTML length={len(data)}")
            
            if not has_pageNumber or not has_products:
                logging.warning(f"Missing required fields: pageNumber={has_pageNumber}, products={has_products}")
                preview_start = data[:2000] if len(data) > 2000 else data
                preview_end = data[-2000:] if len(data) > 2000 else ""
                logging.warning(f"HTML preview (first 2000 chars): {preview_start}")
                if preview_end:
                    logging.warning(f"HTML preview (last 2000 chars): {preview_end}")
                
                captcha_detected = False
                if 'captcha' in data.lower() or 'капча' in data.lower() or 'recaptcha' in data.lower():
                    logging.error("CAPTCHA detected in response!")
                    captcha_detected = True
                if 'blocked' in data.lower() or 'заблокирован' in data.lower():
                    logging.error("Blocked response detected!")
                if 'access denied' in data.lower() or 'доступ запрещен' in data.lower():
                    logging.error("Access denied in response!")
                
                if captcha_detected and proxy:
                    proxyErrorCount[proxy] = proxyErrorCount.get(proxy, 0) + 1
                    if proxyErrorCount[proxy] >= 2:
                        block_time = 15 * 60
                    else:
                        block_time = 10 * 60
                    logging.warning(f"Blocking proxy {proxy[:50]}... for {block_time//60} minutes due to CAPTCHA (errors: {proxyErrorCount[proxy]})")
                    proxyDict[proxy] = time.time() + block_time
                    proxyBlockedTime[proxy] = time.time()
                    return 'CAPTCHA'
            
            pageNumber_pattern = r'"pageNumber"\s*:\s*\d+'
            pageNumber_matches = list(re.finditer(pageNumber_pattern, data))
            
            logging.info(f"Found {len(pageNumber_matches)} 'pageNumber' matches")
            
            for idx, pn_match in enumerate(pageNumber_matches):
                pn_start = pn_match.start()
                search_end = min(len(data), pn_start + 100000)
                search_area = data[pn_start:search_end]
                
                if '"products"' in search_area or '"products":' in search_area:
                    logging.info(f"Match {idx+1}: Found 'products' near 'pageNumber' at position {pn_start}")
                    
                    search_start = max(0, pn_start - 50000)
                    search_end = min(len(data), pn_start + 100000)
                    search_area = data[search_start:search_end]
                    
                    bracket_positions = []
                    for i, char in enumerate(search_area):
                        if char == '{':
                            bracket_positions.append(search_start + i)
                    
                    for bracket_pos in reversed(bracket_positions):
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
                            obj_text = data[start:end]
                            if '"pageNumber"' in obj_text and '"products"' in obj_text:
                                try:
                                    pageJS = json.loads(obj_text)
                                    if 'pageNumber' in pageJS and 'products' in pageJS:
                                        logging.info(f"Found page object with pageNumber={pageJS.get('pageNumber')} and {len(pageJS.get('products', []))} products")
                                        return {'page': pageJS}
                                    elif 'page' in pageJS and isinstance(pageJS['page'], dict):
                                        page_obj = pageJS['page']
                                        if 'pageNumber' in page_obj and 'products' in page_obj:
                                            logging.info(f"Found page object inside 'page' key with pageNumber={page_obj.get('pageNumber')} and {len(page_obj.get('products', []))} products")
                                            return {'page': page_obj}
                                        elif 'pageNumber' in page_obj and 'products' in pageJS:
                                            combined = {**page_obj, 'products': pageJS['products']}
                                            logging.info(f"Found page object (combined) with pageNumber={combined.get('pageNumber')} and {len(combined.get('products', []))} products")
                                            return {'page': combined}
                                    elif 'products' in pageJS:
                                        if 'page' in pageJS and isinstance(pageJS['page'], dict) and 'pageNumber' in pageJS['page']:
                                            combined = {**pageJS['page'], 'products': pageJS['products']}
                                            logging.info(f"Found page object (combined from nested) with pageNumber={combined.get('pageNumber')} and {len(combined.get('products', []))} products")
                                            return {'page': combined}
                                    else:
                                        logging.info(f"Match {idx+1}: Object contains both fields in text but missing in parsed JSON. Keys: {list(pageJS.keys())[:10]}")
                                except json.JSONDecodeError:
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
        
        # Запасной разбор: ключ "pageview" в legacy-разметке.
        try:
            key = '"pageview",'
            pattern = key + r'\s*(\{.*?\})'
            if pageJS := recjson(pattern, data):
                logging.info("Found data using old pageview pattern")
                return pageJS
        except Exception as e:
            logging.warning(f"Error in old pageview pattern: {e}")
    
    return {}


def fetch_flat_page_requests_proxies(
    flat_id: str, max_tries: int = 8, request_timeout: int = 20
) -> str | None:
    """HTML объявления: requests с ротацией прокси из proxyDict (без Playwright)."""
    import requests

    url = f"{URL}/rent/flat/{flat_id}/"
    check_and_unfreeze_proxies()
    load_proxy_bans()

    non_empty = {k: v for k, v in proxyDict.items() if k}
    if non_empty:
        mintime = min(non_empty.values())
        if mintime > time.time():
            wait = mintime - time.time()
            # Ожидание разблокировки прокси только если осталось < 10 с.
            if wait < 10:
                time.sleep(min(wait, 8.0))
            else:
                logging.info(
                    "fetch_flat_page_requests_proxies: proxies cooling %.0fs, skip wait", wait
                )

    available = [
        k
        for k, v in proxyDict.items()
        if k and v <= time.time() and not proxyTemporaryBan.get(k, False)
    ]
    random.shuffle(available)
    proxy_order = available[:max_tries] if available else []
    if not proxy_order:
        proxy_order = [None]

    hdr_list = headers if headers else [{}]
    for proxy in proxy_order:
        try:
            kw: dict = {"headers": random.choice(hdr_list), "timeout": request_timeout}
            if proxy:
                kw["proxies"] = {"http": proxy, "https": proxy}
            r = requests.get(url, **kw)
            if r.status_code != 200:
                continue
            text = r.text
            if '"offerData"' not in text:
                continue
            low = text.lower()
            if "tmgrdfrend/showcaptcha" in low:
                continue
            return text
        except Exception as e:
            if proxy:
                proxyDict[proxy] = time.time() + 90
            logging.debug("fetch_flat_page_requests_proxies: %s", e)
            continue
    return None


def _html_has_usable_offer_data(html: str | None) -> bool:
    if not html or '"offerData"' not in html:
        return False
    low = html.lower()
    if "tmgrdfrend/showcaptcha" in low:
        return False
    return True


def race_fetch_flat_html_for_api(flat_id: str, wait_seconds: float = 20.0) -> str | None:
    """Три загрузчика HTML в ThreadPool; возврат при первом результате с offerData без CAPTCHA."""
    fid = str(flat_id)

    def run_http():
        try:
            return fetch_flat_page_html_http(fid, timeout=min(14.0, wait_seconds))
        except Exception:
            return None

    def run_curl():
        try:
            return fetch_flat_page_curl_cffi_direct(fid, timeout=min(18.0, wait_seconds))
        except Exception:
            return None

    def run_req():
        try:
            return fetch_flat_page_requests_proxies(
                fid, max_tries=6, request_timeout=min(14, int(wait_seconds))
            )
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(run_http), pool.submit(run_curl), pool.submit(run_req)]
        try:
            for fut in as_completed(futures, timeout=wait_seconds):
                try:
                    html = fut.result()
                except Exception:
                    continue
                if _html_has_usable_offer_data(html):
                    return html
        except TimeoutError:
            logging.info("race_fetch_flat_html_for_api: общий таймаут %.0fs flat_id=%s", wait_seconds, fid)
    return None


def _orm_row_to_param_dict(row) -> dict:
    """Поля строки SQLAlchemy → dict для Params (без служебных колонок)."""
    from decimal import Decimal

    out: dict = {}
    for col in row.__table__.columns:
        if col.name in ("id", "created_at", "updated_at"):
            continue
        val = getattr(row, col.name)
        if isinstance(val, Decimal):
            val = float(val)
        out[col.name] = val
    return out


def flat_params_dict_from_db(cian_id: str) -> dict | None:
    """
    Если объявление уже в MySQL (спарсил фоновый parser), собрать ту же структуру, что даёт pagecheck,
    без запроса к сайту Циана.
    """
    try:
        cid = int(cian_id)
    except (TypeError, ValueError):
        return None
    offer_rows = DB.select(model_classes["offers"], filter_by={"cian_id": cid}, limit=1)
    if not offer_rows:
        logging.info("flat_params_dict_from_db: нет offers для cian_id=%s", cian_id)
        return None
    data: dict = {"offers": _orm_row_to_param_dict(offer_rows[0])}
    for key, model in model_classes.items():
        if key in ("photos", "offers"):
            continue
        rows = DB.select(model, filter_by={"cian_id": cid}, limit=1)
        if rows:
            data[key] = _orm_row_to_param_dict(rows[0])
        else:
            data[key] = {"cian_id": cid}
    return data


def parse_rent_flat_for_api(flat_id: str) -> dict | None:
    """Разбор одного объявления для /getparams: параллельные HTTP-загрузки HTML, без Playwright."""
    try:
        html = race_fetch_flat_html_for_api(flat_id, wait_seconds=38.0)
    except Exception as e:
        logging.warning("parse_rent_flat_for_api: гонка загрузчиков flat_id=%s err=%s", flat_id, e)
        html = None
    if not html:
        logging.warning("parse_rent_flat_for_api: no HTML for flat_id=%s", flat_id)
        return None
    page_js = prePage(html, type=1)
    if not page_js:
        logging.warning("parse_rent_flat_for_api: prePage empty for flat_id=%s", flat_id)
        return None
    data = pagecheck(page_js)
    if not data:
        return None
    data.pop("photos", None)
    return data


def listPages(page, sort=None, rooms=None):
    logging.info(f"listPages: Starting for page={page}, sort={sort}, rooms={rooms}")
    pagesList = []
    response = getResponse(page, type=0, sort=sort, rooms=rooms)
    
    if response == 'CAPTCHA':
        logging.warning(f"listPages: CAPTCHA detected for page={page}, sort={sort}, rooms={rooms}, skipping page")
        return []
    
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
    """Обход cian_id: вставка/обновление в БД или один dict при dbinsert=False (до max_retries на id)."""
    pages_cnt = 0
    skipped_count = 0
    existing_count = 0
    filtered_count = 0
    failed_pages = {}
    
    for page in pagesList:
        exist = False
        if dbinsert and DB.select(model_classes['offers'], filter_by={'cian_id': page}):
            exist = True
            existing_count += 1
            logging.info(f"Apart page {page} already exists")
            continue
        
        retry_count = failed_pages.get(page, 0)
        if retry_count >= max_retries:
            skipped_count += 1
            logging.info(f"Apart page {page} skipped after {retry_count} failed attempts")
            continue

        if not dbinsert:
            html_fast = race_fetch_flat_html_for_api(str(page), wait_seconds=22.0)
            if html_fast:
                page_js_fast = prePage(html_fast, type=1)
                if page_js_fast and (data_fast := pagecheck(page_js_fast)):
                    data_fast.pop("photos", None)
                    logging.info("Apart page %s parsed via fast HTTP (getparams)", page)
                    return data_fast
            logging.info("Apart page %s: fast HTTP miss, fallback to getResponse", page)

        use_px = bool(dbinsert)
        response = getResponse(page, type=1, dbinsert=dbinsert, respTry=2, use_proxy=use_px)
        if not dbinsert and (not response or response == "CAPTCHA"):
            response = getResponse(page, type=1, dbinsert=dbinsert, respTry=2, use_proxy=True)
        
        if response == 'CAPTCHA':
            logging.warning(f"Apart page {page}: CAPTCHA detected, skipping")
            filtered_count += 1
            continue
        
        if not response:
            failed_pages[page] = retry_count + 1
            if retry_count + 1 < max_retries:
                logging.info(f"Apart page {page} failed, will retry later (attempt {retry_count + 1}/{max_retries})")
            continue
        
        pageJS = prePage(response, type=1)
        if data := pagecheck(pageJS):
            photos_data = data.pop('photos', [])
            if not dbinsert:
                return data
            if exist:
                existing_count += 1
                instances = [(model, data[key])
                             for key, model in model_classes.items() if key in data]
                for model, update_values in instances:
                    logging.info(f"Apart page {page}, table {model} is updating")
                    DB.update(model, {'cian_id': page}, update_values)
                
                if photos_data:
                    from .database import Photos
                    session = DB.Session()
                    try:
                        session.query(Photos).filter(Photos.cian_id == page).delete()
                        session.commit()
                    except Exception as e:
                        session.rollback()
                        logging.error(f"Error deleting old photos for {page}: {e}")
                    finally:
                        session.close()
                    
                    photo_instances = [Photos(**photo) for photo in photos_data]
                    if photo_instances:
                        DB.insert(*photo_instances)
                        logging.info(f"Apart page {page}: added {len(photo_instances)} photos")
            else:
                instances = [model(**data[key])
                             for key, model in model_classes.items() if key in data]
                logging.info(f"Apart page {page} is adding")
                DB.insert(*instances)
                
                if photos_data:
                    from .database import Photos
                    photo_instances = [Photos(**photo) for photo in photos_data]
                    if photo_instances:
                        DB.insert(*photo_instances)
                        logging.info(f"Apart page {page}: added {len(photo_instances)} photos")
            pages_cnt += 1
            if page in failed_pages:
                del failed_pages[page]
        else:
            filtered_count += 1
            failed_pages[page] = retry_count + 1
            if retry_count + 1 < max_retries:
                logging.info(f"Apart page {page} parse failed, will retry later (attempt {retry_count + 1}/{max_retries})")
        continue
    
    logging.info(f"Apart pages {pagesList[:5]}{'...' if len(pagesList) > 5 else ''} processed. Added: {pages_cnt}, Existing: {existing_count}, Filtered: {filtered_count}, Skipped: {skipped_count}")

    # Один id и dbinsert=False: коды OK/FILTERED строками, клиент ожидает dict или None.
    if len(pagesList) == 1 and not dbinsert:
        return None

    if pages_cnt > 0:
        logging.info(f"SUCCESS: Added {pages_cnt} new offers from {len(pagesList)} total")
        return 'OK'
    
    if existing_count > 0 and pages_cnt == 0 and filtered_count == 0:
        logging.info(f"All {existing_count} offers already exist in database")
        return 'EXISTING'
    
    if filtered_count > 0 and pages_cnt == 0:
        logging.info(f"All {filtered_count} offers were filtered out")
        return 'FILTERED'
    
    if skipped_count > 0 and pages_cnt == 0:
        logging.warning(f"All {skipped_count} offers were skipped due to errors/CAPTCHA")
        return 'SKIPPED'
    
    if len(pagesList) == 0:
        logging.warning("Empty pagesList passed to apartPage")
        return None
    
    return 'OK'

