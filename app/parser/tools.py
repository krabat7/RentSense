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

# Загружаем .env из корня проекта
env_path = Path(__file__).parent.parent.parent / '.env'
env = dotenv_values(env_path)
proxyDict = {}
 i = 1
 while True:
     proxy = env.get(f'PROXY{i}')
     if proxy:
         proxyDict[proxy] = 0.0
         i += 1
     else:
         break  # Прекращаем, когда больше нет прокси
proxyDict[''] = 0.0

# Логируем количество загруженных прокси
logging.info(f'Loaded {len([p for p in proxyDict.keys() if p != ""])} proxies from .env file')

# Словарь для отслеживания времени последней блокировки прокси
# Используется для разморозки заблокированных прокси
# Инициализируем после заполнения proxyDict
proxyBlockedTime = {proxy: 0.0 for proxy in proxyDict.keys()}

# Счетчик ошибок для каждого прокси (не блокируем сразу после первой ошибки)
proxyErrorCount = {proxy: 0 for proxy in proxyDict.keys()}

# Счетчик ошибок подключения для каждого прокси (ERR_PROXY_CONNECTION_FAILED)
proxyConnectionErrors = {proxy: 0 for proxy in proxyDict.keys()}

# Временный бан прокси (полное исключение из ротации, даже если разблокирован)
# Используется для "отдыха" прокси или тестирования новых прокси
proxyTemporaryBan = {proxy: False for proxy in proxyDict.keys()}

# Файл для сохранения временных банов прокси (синхронизация между процессами)
PROXY_BANS_FILE = Path(__file__).parent.parent.parent / '.proxy_bans'

def load_proxy_bans():
    """Загружает временно забаненные прокси из файла."""
    global proxyTemporaryBan
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
    # Если файла нет - это нормально, не логируем каждый раз

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
    """
    Проверяет заблокированные прокси и размораживает их через определенное время.
    Это позволяет прокси "отдохнуть" и снова начать работать.
    """
    current_time = time.time()
    unfrozen_count = 0
    
    for proxy, blocked_until in proxyDict.items():
        # Пропускаем временно забаненные прокси
        if proxyTemporaryBan.get(proxy, False):
            continue
            
        # Если прокси заблокирован более чем на 5 минут, проверяем его
        if blocked_until > current_time:
            blocked_duration = blocked_until - current_time
            # Если прокси заблокирован более 5 минут, пробуем разморозить через 10 минут после блокировки
            if blocked_duration > (5 * 60) and proxyBlockedTime[proxy] > 0:
                time_since_block = current_time - proxyBlockedTime[proxy]
                # Размораживаем через 10 минут после блокировки (или если прошло больше 30 минут)
                if time_since_block > (10 * 60) or blocked_duration > (30 * 60):
                    logging.info(f'Attempting to unfreeze proxy {proxy[:20]}... (blocked for {blocked_duration/60:.1f} min)')
                    # Сбрасываем время блокировки, но оставляем небольшую задержку
                    proxyDict[proxy] = current_time + 30  # Даем 30 секунд перед повторным использованием
                    proxyBlockedTime[proxy] = 0
                    unfrozen_count += 1
    
    if unfrozen_count > 0:
        logging.info(f'Unfrozen {unfrozen_count} proxy/proxies')
    
    return unfrozen_count


def ban_proxies_by_pattern(pattern='', exclude_patterns=None):
    """
    Временно блокирует прокси по паттерну (например, по части IP или имени).
    exclude_patterns - список паттернов для исключения (например, новые прокси)
    """
    load_proxy_bans()  # Загружаем текущие баны перед изменением
    banned_count = 0
    for proxy in proxyDict.keys():
        if proxy == '':
            continue
        if pattern and pattern in proxy:
            # Проверяем исключения
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
    """
    Разбан всех прокси и сброс всех счетчиков ошибок (для "ресета" прокси).
    """
    load_proxy_bans()  # Загружаем текущие баны перед изменением
    unbanned_count = 0
    current_time = time.time()
    
    for proxy in proxyDict.keys():
        if proxyTemporaryBan.get(proxy, False):
            proxyTemporaryBan[proxy] = False
            unbanned_count += 1
            
        # Сбрасываем все счетчики
        proxyErrorCount[proxy] = 0
        proxyConnectionErrors[proxy] = 0
        proxyBlockedTime[proxy] = 0
        
        # Разблокируем прокси (ставим время блокировки в прошлое)
        proxyDict[proxy] = current_time - 1
    
    save_proxy_bans()  # Сохраняем изменения
    logging.info(f'Unbanned {unbanned_count} proxies and reset all error counters')
    return unbanned_count

headers = [
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.90 Safari/537.36"},
    {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Safari/605.1.15"},
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/118.0"},
    {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:118.0) Gecko/20100101 Firefox/118.0"},
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; Trident/7.0; AS; rv:11.0) like Gecko"},
]
