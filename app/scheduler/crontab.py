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
    # 0 = без паузы (непрерывная работа), 60 = 1 минута (минимальная пауза)
    PARSE_INTERVAL = 60  # 1 минута между циклами (уменьшено с 30 минут для непрерывной работы)
    
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
        
        # Минимальная пауза перед следующим циклом (для непрерывной работы)
        if PARSE_INTERVAL > 0:
            logging.info(f"Короткая пауза {PARSE_INTERVAL} секунд перед следующим циклом...")
            await asyncio.sleep(PARSE_INTERVAL)
        else:
            logging.info("Переход к следующему циклу без паузы...")


if __name__ == "__main__":
    asyncio.run(cron())


