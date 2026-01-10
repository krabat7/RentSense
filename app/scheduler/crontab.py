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
    # 3600 = 1 час, 1800 = 30 минут, 900 = 15 минут, 600 = 10 минут
    PARSE_INTERVAL = 60  # 1 минута (уменьшено с 30 минут)  # 30 минут (уменьшено с 60)  # 60 минут между полными циклами (увеличено для большего количества новых объявлений) (настраивается)
    
    cycle_number = 0
    
    logging.info("=== Парсер запущен: непрерывный режим ===")
    logging.info(f"Интервал между циклами: {PARSE_INTERVAL} секунд ({PARSE_INTERVAL // 60} минут)")
    
    while True:
        cycle_number += 1
        logging.info(f"=== Начало цикла парсинга #{cycle_number} ===")
        
        try:
            # Запуск парсинга (всегда начинаем с первой страницы для поиска новых объявлений)
            await parsing(page=1)
            logging.info(f"=== Цикл парсинга #{cycle_number} завершен успешно ===")
        except Exception as e:
            logging.error(f"Ошибка в цикле парсинга #{cycle_number}: {e}", exc_info=True)
        
        # Ждем перед следующим циклом
        logging.info(f"Короткая пауза {PARSE_INTERVAL} секунд ({PARSE_INTERVAL // 60} минут) перед следующим циклом...")
        await asyncio.sleep(PARSE_INTERVAL)


if __name__ == "__main__":
    asyncio.run(cron())
