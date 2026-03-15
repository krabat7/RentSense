import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from app.parser.main import apartPage, listPages

# Используем ThreadPoolExecutor с одним воркером для изоляции синхронного Playwright кода
# Playwright sync API не может работать в разных потоках одновременно
executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="parser_thread")

# Максимальное время выполнения парсинга (в секундах)
MAX_PARSING_TIME = 7200  # 2 часа (совпадает с MAX_CYCLE_TIME в crontab.py)

ROOMS = ['', 'room1', 'room2', 'room3', 'room4', 'room5', 'room6', 'room7', 'room8', 'room9']
SORTS = ['creation_date_desc', 'creation_date_asc']


def _process_page(start_page, sort, room):
    """Парсит страницы начиная с start_page. Останавливается при END, 3 пустых подряд или 20 ошибках."""
    current_page = start_page
    errors = 0
    new_offers_count = 0
    existing_offers_count = 0
    consecutive_empty_pages = 0
    while errors < 20:
        pglist = listPages(current_page, sort, room)
        if pglist == 'END':
            logging.info(f'End of pglist reached (END) for room={room}, sort={sort}, page={current_page}')
            break
        if pglist is None:
            logging.warning(f'listPages returned None for room={room}, sort={sort}, page={current_page}')
            errors += 1
            if errors >= 20:
                break
            current_page += 1
            continue
        if isinstance(pglist, list) and len(pglist) == 0:
            consecutive_empty_pages += 1
            logging.info(f'Empty page {current_page} for room={room}, sort={sort} (consecutive empty: {consecutive_empty_pages})')
            if consecutive_empty_pages >= 3:
                break
            current_page += 1
            continue
        consecutive_empty_pages = 0
        data = apartPage(pglist, dbinsert=True)
        if data == 'END':
            break
        if data is None:
            errors += 1
            if errors >= 20:
                break
        elif data == 'SKIPPED':
            errors += 1
            if errors >= 20:
                break
        elif data == 'OK':
            errors = 0
            new_offers_count += 1
        elif data in ['EXISTING', 'FILTERED']:
            errors = 0
            if data == 'EXISTING':
                existing_offers_count += 1
        current_page += 1
    logging.info(f'Finished: room={room}, sort={sort}, pages={current_page - start_page}, new={new_offers_count}, existing={existing_offers_count}')


def run_one_cycle_sync():
    """
    Один цикл парсинга в текущем потоке (для запуска в подпроцессе).
    При убийстве процесса браузер и ресурсы освобождаются ОС.
    """
    start_time = time.time()
    for room in ROOMS:
        for sort in SORTS:
            if time.time() - start_time > MAX_PARSING_TIME:
                logging.warning(f'Превышено максимальное время парсинга ({MAX_PARSING_TIME // 60} минут), прерываем цикл')
                return
            logging.info(f'Starting parsing: room={room or "all"}, sort={sort or "default"}, page=1')
            _process_page(1, sort, room)
            logging.info(f'Finished: room={room or "all"}, sort={sort or "default"}')
    logging.info(f'Все комбинации обработаны за {time.time() - start_time:.1f} секунд')


async def parsing(page=1):
    """
    Парсинг объявлений с первой страницы для поиска новых объявлений.
    Запускается в executor (один поток) для изоляции Playwright.
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, run_one_cycle_sync)


