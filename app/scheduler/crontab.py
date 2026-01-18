import asyncio
import logging
import nest_asyncio
from .tasks import parsing

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Разрешить вложенные event loops для Playwright
nest_asyncio.apply()


async def cron():
    """
    Непрерывный парсинг: постоянно ищет и парсит новые объявления.
    После каждого полного цикла ждет заданное время перед следующим запуском.
    """
    # Интервал между полными циклами парсинга (в секундах)
    # Увеличено до 30 минут для более естественного поведения и снижения риска CAPTCHA
    PARSE_INTERVAL = 1800  # 30 минут между циклами (увеличено с 10 минут)
    
    cycle_number = 0
    
    logging.info("=== Парсер запущен: непрерывный режим ===")
    logging.info(f"Интервал между циклами: {PARSE_INTERVAL} секунд ({PARSE_INTERVAL // 60} минут)")
    
    # Максимальное время выполнения одного цикла парсинга (в секундах)
    # 7200 = 2 часа, если парсинг зависнет, цикл все равно завершится
    MAX_CYCLE_TIME = 7200  # 2 часа
    
    while True:
        cycle_number += 1
        cycle_start_time = asyncio.get_event_loop().time()
        logging.info(f"=== Начало цикла парсинга #{cycle_number} ===")
        
        try:
            # Запуск парсинга с таймаутом (всегда начинаем с первой страницы для поиска новых объявлений)
            # Если парсинг зависнет более чем на MAX_CYCLE_TIME, он будет прерван
            await asyncio.wait_for(parsing(page=1), timeout=MAX_CYCLE_TIME)
            cycle_duration = asyncio.get_event_loop().time() - cycle_start_time
            logging.info(f"=== Цикл парсинга #{cycle_number} завершен успешно за {cycle_duration:.1f} секунд ===")
        except asyncio.TimeoutError:
            cycle_duration = asyncio.get_event_loop().time() - cycle_start_time
            logging.error(f"Цикл парсинга #{cycle_number} превысил максимальное время ({MAX_CYCLE_TIME // 60} минут) и был прерван после {cycle_duration:.1f} секунд. Возможно, парсер завис.")
            # Принудительно закрываем браузер при таймауте, чтобы освободить ресурсы
            try:
                from app.parser.main import close_browser
                close_browser()
                logging.info("Браузер закрыт после таймаута")
            except Exception as e:
                logging.warning(f"Не удалось закрыть браузер после таймаута: {e}")
        except Exception as e:
            cycle_duration = asyncio.get_event_loop().time() - cycle_start_time
            logging.error(f"Ошибка в цикле парсинга #{cycle_number} после {cycle_duration:.1f} секунд: {e}", exc_info=True)
            # Принудительно закрываем браузер при ошибке
            try:
                from app.parser.main import close_browser
                close_browser()
                logging.info("Браузер закрыт после ошибки")
            except Exception as e2:
                logging.warning(f"Не удалось закрыть браузер после ошибки: {e2}")
        
        # Ждем перед следующим циклом
        logging.info(f"Короткая пауза {PARSE_INTERVAL} секунд ({PARSE_INTERVAL // 60} минут) перед следующим циклом...")
        try:
            await asyncio.sleep(PARSE_INTERVAL)
        except Exception as e:
            logging.error(f"Ошибка при ожидании перед следующим циклом: {e}", exc_info=True)
            # Если даже sleep упал, ждем еще немного перед продолжением
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(cron())
