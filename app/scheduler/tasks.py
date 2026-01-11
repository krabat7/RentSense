import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from app.parser.main import apartPage, listPages

# Используем ThreadPoolExecutor с одним воркером для изоляции синхронного Playwright кода
# Playwright sync API не может работать в разных потоках одновременно
executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="parser_thread")


async def parsing(page=1):
    """
    Парсинг объявлений с первой страницы для поиска новых объявлений.
    Всегда начинаем с page=1, чтобы находить самые свежие объявления.
    """
    rooms = ['', 'room1', 'room2', 'room3', 'room4', 'room5', 'room6', 'room7', 'room8', 'room9']
    sorts = ['', 'creation_date_asc', 'creation_date_desc']

    def process_page(start_page, sort, room):
        """
        Парсит страницы начиная с start_page.
        Останавливается при достижении конца или при большом количестве ошибок.
        """
        current_page = start_page
        errors = 0
        new_offers_count = 0
        existing_offers_count = 0
        
        consecutive_empty_pages = 0  # Счетчик пустых страниц подряд
        
        while errors < 20:  # Уменьшено с 30 до 20 для более быстрого пропуска проблем
            pglist = listPages(current_page, sort, room)
            
            # 'END' означает, что страница не найдена или это конец списка
            if pglist == 'END':
                logging.info(f'End of pglist reached (END) for room={room}, sort={sort}, page={current_page}')
                break
            
            # None означает критическую ошибку (getResponse вернул None)
            if pglist is None:
                logging.warning(f'listPages returned None for room={room}, sort={sort}, page={current_page}')
                errors += 1
                if errors >= 20:
                    logging.info(f'Error limit {errors} reached, stopping')
                    break
                current_page += 1
                continue
            
            # Пустой список [] означает, что объявлений на странице нет (но страница существует)
            if isinstance(pglist, list) and len(pglist) == 0:
                consecutive_empty_pages += 1
                logging.info(f'Empty page {current_page} for room={room}, sort={sort} (consecutive empty: {consecutive_empty_pages})')
                if consecutive_empty_pages >= 3:  # Если 3 пустые страницы подряд - останавливаемся
                    logging.info(f'3 consecutive empty pages, stopping for room={room}, sort={sort}')
                    break
                current_page += 1
                continue
            else:
                consecutive_empty_pages = 0  # Сбрасываем счетчик при успехе
            
            # Парсим страницу со списком объявлений
            data = apartPage(pglist, dbinsert=True)
            if data == 'END':
                logging.info(f'End of data reached for room={room}, sort={sort}, page={current_page}')
                break
            
            if not data:
                errors += 1
                logging.info(f'Error parse count: {errors} for page={current_page}, room={room}, sort={sort}')
                if errors >= 20:  # Уменьшено с 30 до 20
                    logging.info(f'Error limit {errors} reached, stopping')
                    break
            else:
                # Если данные успешно обработаны, считаем это успешным парсингом
                errors = 0
                new_offers_count += 1
            
            current_page += 1
            
            # Ограничение на максимальное количество страниц за один запуск
            # Уменьшено с 50 до 30 для более быстрого перехода к новым объявлениям
            if current_page > start_page + 30:
                logging.info(f'Reached page limit (30 pages) for room={room}, sort={sort}')
                break
        
        logging.info(f'Finished: room={room}, sort={sort}, pages={current_page - start_page}, new={new_offers_count}, existing={existing_offers_count}')

    def theard():
        """
        Запускает парсинг для всех комбинаций room и sort последовательно.
        Всегда начинаем с первой страницы для поиска новых объявлений.
        Прокси будут использоваться автоматически с улучшенной логикой выбора.
        """
        for room in rooms:
            for sort in sorts:
                logging.info(f'Starting parsing: room={room or "all"}, sort={sort or "default"}, page=1')
                process_page(1, sort, room)  # Всегда начинаем с первой страницы
                logging.info(f'Finished: room={room or "all"}, sort={sort or "default"}')

    # Используем executor для изоляции синхронного Playwright кода
    # Обрабатываем последовательно, но прокси будут использоваться эффективно
    # благодаря улучшенной логике выбора и автоматической разморозке
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, theard)
