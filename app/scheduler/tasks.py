import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from app.parser.main import apartPage, listPages

# Используем ThreadPoolExecutor с одним воркером для изоляции синхронного Playwright кода
# Playwright sync API не может работать в разных потоках одновременно
executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="parser_thread")

# Максимальное время выполнения парсинга (в секундах)
# Если парсинг займет больше этого времени, он будет прерван
MAX_PARSING_TIME = 7200  # 2 часа (совпадает с MAX_CYCLE_TIME в crontab.py)


async def parsing(page=1):
    """
    Парсинг объявлений с первой страницы для поиска новых объявлений.
    Всегда начинаем с page=1, чтобы находить самые свежие объявления.
    """
    rooms = ['', 'room1', 'room2', 'room3', 'room4', 'room5', 'room6', 'room7', 'room8', 'room9']
    sorts = ['', 'creation_date_asc', 'creation_date_desc']

    def find_start_page(sort, room):
        """
        Находит хорошую стартовую страницу, начиная с большой (500) и идя назад.
        Это позволяет быстрее найти новые объявления, не тратя время на поиск точной последней страницы.
        """
        # Начинаем с большой страницы (500) и идем назад с большим шагом
        test_page = 500
        valid_page = 1  # По умолчанию начинаем с первой
        attempts = 0
        max_attempts = 10  # Максимум 10 попыток найти валидную страницу
        
        # Быстрый поиск: проверяем страницы с шагом 50
        while test_page >= 1 and attempts < max_attempts:
            attempts += 1
            pglist = listPages(test_page, sort, room)
            
            # Если получили CAPTCHA или все прокси заблокированы, пробуем меньшую страницу
            if pglist == 'END' or pglist is None:
                # Страница не существует, пробуем меньшую
                test_page -= 50
                if test_page < 1:
                    break
            elif isinstance(pglist, list):
                if len(pglist) > 0:
                    # Нашли валидную страницу с объявлениями
                    valid_page = test_page
                    logging.info(f'Found valid start page: {valid_page} for room={room or "all"}, sort={sort or "default"}')
                    return valid_page
                else:
                    # Пустая страница (возможно CAPTCHA), пробуем меньшую
                    test_page -= 50
            else:
                # Неожиданный результат, пробуем меньшую страницу
                test_page -= 50
        
        # Если не нашли валидную страницу, используем рандомную страницу в диапазоне 100-300
        # Это лучше, чем начинать с первой страницы
        import random
        fallback_page = random.randint(100, 300)
        logging.info(f'Using fallback start page: {fallback_page} for room={room or "all"}, sort={sort or "default"}')
        return fallback_page
    
    def process_page(start_page, sort, room, reverse=False):
        """
        Парсит страницы начиная с start_page.
        Если reverse=True, идет назад от start_page.
        Останавливается при достижении конца или при большом количестве ошибок.
        """
        current_page = start_page
        errors = 0
        new_offers_count = 0
        existing_offers_count = 0
        
        consecutive_empty_pages = 0  # Счетчик пустых страниц подряд
        page_direction = -1 if reverse else 1  # Направление движения по страницам
        
        while errors < 20:  # Уменьшено с 30 до 20 для более быстрого пропуска проблем
            pglist = listPages(current_page, sort, room)
            
            # 'END' означает, что страница не найдена или это конец списка
            if pglist == 'END':
                if reverse:
                    # Если идем назад и дошли до конца, переключаемся на движение вперед
                    logging.info(f'End of pglist reached (END) while going reverse, switching to forward from page {start_page}')
                    reverse = False
                    page_direction = 1
                    current_page = start_page + 1
                    continue
                else:
                    logging.info(f'End of pglist reached (END) for room={room}, sort={sort}, page={current_page}')
                    break
            
            # None означает критическую ошибку (getResponse вернул None)
            if pglist is None:
                logging.warning(f'listPages returned None for room={room}, sort={sort}, page={current_page}')
                errors += 1
                if errors >= 20:
                    logging.info(f'Error limit {errors} reached, stopping')
                    break
                current_page += page_direction
                # Если идем назад и дошли до страницы 1, переключаемся на движение вперед
                if reverse and current_page < 1:
                    logging.info(f'Reached page 1, switching to forward direction from page {start_page}')
                    reverse = False
                    page_direction = 1
                    current_page = start_page + 1
                continue
            
            # Пустой список [] означает, что объявлений на странице нет (но страница существует)
            # Это может быть из-за CAPTCHA или действительно пустых страниц
            if isinstance(pglist, list) and len(pglist) == 0:
                consecutive_empty_pages += 1
                logging.info(f'Empty page {current_page} for room={room}, sort={sort} (consecutive empty: {consecutive_empty_pages})')
                # Если много пустых страниц подряд, пропускаем комбинацию
                if consecutive_empty_pages >= 10:  # Возвращено к 10 - работало раньше
                    logging.info(f'{consecutive_empty_pages} consecutive empty pages, stopping for room={room}, sort={sort}')
                    break
                current_page += page_direction
                # Если идем назад и дошли до страницы 1, переключаемся на движение вперед
                if reverse and current_page < 1:
                    logging.info(f'Reached page 1, switching to forward direction from page {start_page}')
                    reverse = False
                    page_direction = 1
                    current_page = start_page + 1
                continue
            else:
                consecutive_empty_pages = 0  # Сбрасываем счетчик при успехе
            
            # Парсим страницу со списком объявлений
            data = apartPage(pglist, dbinsert=True)
            if data == 'END':
                logging.info(f'End of data reached for room={room}, sort={sort}, page={current_page}')
                break
            
            # Если data == 'OK' - объявления были обработаны (даже если все уже были в базе)
            # Если data == None - это не обязательно ошибка, возможно все объявления уже в базе или отфильтрованы
            # Считаем ошибкой только если на странице были объявления, но парсинг не удался
            if data == 'OK':
                # Если данные успешно обработаны, считаем это успешным парсингом
                errors = 0
                new_offers_count += 1
            elif data is None:
                # Если data == None, это может быть:
                # 1. Все объявления уже в базе (не ошибка)
                # 2. Все объявления отфильтрованы (не ошибка)
                # 3. Ошибка парсинга (ошибка)
                # Увеличиваем счетчик ошибок только если на странице были объявления
                if len(pglist) > 0:
                    errors += 1
                    logging.info(f'Parse returned None for page={current_page}, room={room}, sort={sort} (had {len(pglist)} offers), error count: {errors}')
                    if errors >= 20:
                        logging.info(f'Error limit {errors} reached, stopping')
                        break
                else:
                    # Если список был пуст, это не ошибка
                    errors = 0
            
            current_page += page_direction
            
            # Если идем назад и дошли до страницы 1, переключаемся на движение вперед
            if reverse and current_page < 1:
                logging.info(f'Reached page 1, switching to forward direction from page {start_page}')
                reverse = False
                page_direction = 1
                current_page = start_page + 1
            
            # Лимит на страницы убран - парсим до конца списка
            # Остановка происходит только при:
            # 1. Достижении конца списка ('END')
            # 2. 10 пустых страницах подряд
            # 3. 20 ошибках подряд
        
        logging.info(f'Finished: room={room}, sort={sort}, pages={current_page - start_page}, new={new_offers_count}, existing={existing_offers_count}')

    def theard():
        """
        Запускает парсинг для всех комбинаций room и sort последовательно.
        Всегда начинаем с первой страницы для поиска новых объявлений.
        Прокси будут использоваться автоматически с улучшенной логикой выбора.
        """
        start_time = time.time()
        skipped_combinations = 0  # Счетчик пропущенных комбинаций из-за CAPTCHA
        
        for room in rooms:
            for sort in sorts:
                # Проверяем, не превысили ли мы максимальное время
                elapsed = time.time() - start_time
                if elapsed > MAX_PARSING_TIME:
                    logging.warning(f'Превышено максимальное время парсинга ({MAX_PARSING_TIME // 60} минут), прерываем цикл')
                    return
                
                # Проверяем, не заблокированы ли все прокси CAPTCHA перед началом комбинации
                # Пропускаем только если все прокси заблокированы более чем на 5 минут
                from app.parser.tools import proxyDict
                non_empty_proxies = {k: v for k, v in proxyDict.items() if k != ''}
                if non_empty_proxies:
                    current_time = time.time()
                    all_blocked = all(v > current_time + (5 * 60) for v in non_empty_proxies.values())  # Все заблокированы >5 минут
                    if all_blocked:
                        min_unlock = min(v for v in non_empty_proxies.values())
                        unlock_time = min_unlock - current_time
                        logging.warning(f'All proxies blocked for {unlock_time/60:.1f} minutes, skipping combination room={room or "all"}, sort={sort or "default"}')
                        skipped_combinations += 1
                        # Если все комбинации пропущены, делаем короткую паузу
                        if skipped_combinations >= len(rooms) * len(sorts) - 1:
                            logging.warning(f'All combinations skipped due to blocked proxies, waiting 1 minute before next cycle')
                            time.sleep(60)  # 1 минута пауза (уменьшено с 5 минут)
                            skipped_combinations = 0
                        continue
                
                # Находим хорошую стартовую страницу (ближе к концу списка) для новых объявлений
                start_page = find_start_page(sort, room)
                if start_page > 10:
                    # Начинаем с найденной страницы и идем назад, затем вперед
                    logging.info(f'Starting parsing: room={room or "all"}, sort={sort or "default"}, from page={start_page} (reverse) (elapsed: {elapsed:.1f}s)')
                    process_page(start_page, sort, room, reverse=True)
                else:
                    # Если не нашли хорошую страницу, начинаем с первой
                    logging.info(f'Starting parsing: room={room or "all"}, sort={sort or "default"}, page=1 (elapsed: {elapsed:.1f}s)')
                    process_page(1, sort, room, reverse=False)
                logging.info(f'Finished: room={room or "all"}, sort={sort or "default"}')
                skipped_combinations = 0  # Сбрасываем счетчик при успешной комбинации
        
        total_time = time.time() - start_time
        logging.info(f'Все комбинации обработаны за {total_time:.1f} секунд ({total_time / 60:.1f} минут)')

    # Используем executor для изоляции синхронного Playwright кода
    # Обрабатываем последовательно, но прокси будут использоваться эффективно
    # благодаря улучшенной логике выбора и автоматической разморозке
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, theard)
