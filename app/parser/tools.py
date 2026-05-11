import json
import logging
import re
import time
from pathlib import Path
from dotenv import dotenv_values

def recjson(regex, data, ident=None):
    match = re.search(regex, data)
    if not match:
        logging.error('Recjson not match')
        return
    start_idx = match.start(1)
    end_idx, open_brackets = start_idx + 1, 1
    while open_brackets > 0 and end_idx < len(data):
        open_brackets += 1 if data[end_idx] == '{' else -1 if data[end_idx] == '}' else 0
        end_idx += 1
    if ident:
        json_str = f"{{'{ident}': {data[start_idx:end_idx]}}}"
    else:
        json_str = data[start_idx:end_idx]
    try:
        fdata = json.loads(json_str)
        return fdata
    except Exception as ex:
        logging.error(f'Recjson error: {ex}')
        return

formatter = '%(asctime)s | %(levelname)s: %(message)s'
datefmt = '%Y-%m-%d %H:%M:%S'
logging.basicConfig(
    format=formatter,
    datefmt=datefmt,
    level=logging.INFO,
    filename='rentsense.log',
    filemode='a'
)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(formatter, datefmt))
logging.getLogger().addHandler(console_handler)

# .env в корне репозитория.
env_path = Path(__file__).parent.parent.parent / '.env'
env = dotenv_values(env_path)

# proxyDict: ключи PROXY1, PROXY2, ... из .env, значение timestamp разблокировки.
proxyDict = {}
i = 1
while True:
    proxy = env.get(f'PROXY{i}')
    if proxy:
        proxyDict[proxy] = 0.0
        i += 1
    else:
        break  # Конец последовательности PROXY{i}.
proxyDict[''] = 0.0

logging.info(f'Loaded {len([p for p in proxyDict.keys() if p != ""])} proxies from .env file')

# Время начала блокировки (для разморозки по таймеру).
proxyBlockedTime = {proxy: 0.0 for proxy in proxyDict.keys()}

# Счётчик ошибок запросов на прокси (ступенчатая блокировка).
proxyErrorCount = {proxy: 0 for proxy in proxyDict.keys()}

# Ошибки подключения к прокси (отдельный счётчик).
proxyConnectionErrors = {proxy: 0 for proxy in proxyDict.keys()}

# Ручной/файловый бан: прокси не участвует в ротации, пока флаг True.
proxyTemporaryBan = {proxy: False for proxy in proxyDict.keys()}

# Список забаненных прокси, общий для процессов (файл в корне проекта).
PROXY_BANS_FILE = Path(__file__).parent.parent.parent / '.proxy_bans'

def load_proxy_bans():
    """Загружает временно забаненные прокси из файла."""
    if PROXY_BANS_FILE.exists():
        try:
            with open(PROXY_BANS_FILE, 'r', encoding='utf-8') as f:
                banned_proxies = {line.strip() for line in f if line.strip()}
            banned_count = 0
            for proxy in proxyDict.keys():
                was_banned = proxyTemporaryBan.get(proxy, False)
                proxyTemporaryBan[proxy] = proxy in banned_proxies
                if proxyTemporaryBan[proxy] and not was_banned:
                    banned_count += 1
            if len(banned_proxies) > 0:
                logging.info(f"Loaded {len(banned_proxies)} temporary bans from {PROXY_BANS_FILE} (applied {banned_count} new bans)")
        except Exception as e:
            logging.error(f"Error loading proxy bans from file {PROXY_BANS_FILE}: {e}")

def save_proxy_bans():
    """Сохраняет временно забаненные прокси в файл."""
    try:
        with open(PROXY_BANS_FILE, 'w', encoding='utf-8') as f:
            for proxy, is_banned in proxyTemporaryBan.items():
                if is_banned:
                    f.write(f"{proxy}\n")
        logging.debug(f"Saved {sum(1 for v in proxyTemporaryBan.values() if v)} temporary bans to {PROXY_BANS_FILE}")
    except Exception as e:
        logging.error(f"Error saving proxy bans to file {PROXY_BANS_FILE}: {e}")

def check_and_unfreeze_proxies():
    """Снимает долгую блокировку с прокси после интервала простоя (разморозка)."""
    current_time = time.time()
    unfrozen_count = 0
    
    for proxy, blocked_until in proxyDict.items():
        # Прокси из proxyTemporaryBan не трогаем.
        if proxyTemporaryBan.get(proxy, False):
            continue
            
        if blocked_until > current_time:
            blocked_duration = blocked_until - current_time
            if blocked_duration > (5 * 60) and proxyBlockedTime[proxy] > 0:
                time_since_block = current_time - proxyBlockedTime[proxy]
                if time_since_block > (10 * 60) or blocked_duration > (30 * 60):
                    logging.info(f'Attempting to unfreeze proxy {proxy[:20]}... (blocked for {blocked_duration/60:.1f} min)')
                    proxyDict[proxy] = current_time + 30  # Короткая задержка перед повторным использованием.
                    proxyBlockedTime[proxy] = 0
                    unfrozen_count += 1
    
    if unfrozen_count > 0:
        logging.info(f'Unfrozen {unfrozen_count} proxy/proxies')
    
    return unfrozen_count


def ban_proxies_by_pattern(pattern='', exclude_patterns=None):
    """Помечает прокси временным баном, если URL содержит pattern (с опциональными exclude)."""
    load_proxy_bans()  # Загружаем текущие баны перед изменением
    banned_count = 0
    for proxy in proxyDict.keys():
        if proxy == '':
            continue
        if pattern and pattern in proxy:
            if exclude_patterns:
                should_exclude = any(exc in proxy for exc in exclude_patterns)
                if should_exclude:
                    continue
            proxyTemporaryBan[proxy] = True
            banned_count += 1
            logging.info(f'Temporarily banned proxy: {proxy[:50]}...')
    save_proxy_bans()  # Сохраняем изменения
    logging.info(f'Banned {banned_count} proxies by pattern "{pattern}"')
    return banned_count


def unban_all_proxies():
    """Снимает временные баны и обнуляет счётчики ошибок по всем прокси."""
    load_proxy_bans()  # Загружаем текущие баны перед изменением
    unbanned_count = 0
    current_time = time.time()
    
    for proxy in proxyDict.keys():
        if proxyTemporaryBan.get(proxy, False):
            proxyTemporaryBan[proxy] = False
            unbanned_count += 1
            
        # Обнуление счётчиков ошибок и времени блокировки.
        proxyErrorCount[proxy] = 0
        proxyConnectionErrors[proxy] = 0
        proxyBlockedTime[proxy] = 0
        
        # proxyDict[proxy] < now: прокси снова доступен.
        proxyDict[proxy] = current_time - 1
    
    save_proxy_bans()  # Сохраняем изменения
    logging.info(f'Unbanned {unbanned_count} proxies and reset all error counters')
    return unbanned_count

# Пул наборов HTTP-заголовков (User-Agent, Referer, Sec-CH-UA) для ротации.
headers = [
    # Chrome / Windows
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "https://www.google.com/",
        "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://yandex.ru/",
        "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "https://www.cian.ru/",
        "Sec-Ch-Ua": '"Google Chrome";v="130", "Chromium";v="130", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.google.com/search?q=cian",
    },
    # Firefox / Windows
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "https://yandex.ru/",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.google.com/",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "https://www.cian.ru/",
    },
    # Edge / Windows
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "https://www.bing.com/",
        "Sec-Ch-Ua": '"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://yandex.ru/",
    },
    # Chrome / macOS
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "https://www.google.com/",
        "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
    },
    # Chrome / Linux
    {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://yandex.ru/",
    },
    # Без Referer
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9",
        "Accept-Encoding": "gzip, deflate, br, zstd",
    },
]
