import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

PARSE_INTERVAL = 1800  # 30 минут между циклами
MAX_CYCLE_TIME = 7200  # 2 часа на цикл; при превышении процесс убивается


async def run_one_cycle_subprocess():
    """Запуск одного цикла в подпроцессе. При таймауте процесс убивается — браузер освобождается ОС."""
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "app.scheduler.run_parser_once",
    )
    try:
        await asyncio.wait_for(proc.wait(), timeout=MAX_CYCLE_TIME)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise
    if proc.returncode != 0:
        raise RuntimeError(f"run_parser_once exited with code {proc.returncode}")


async def cron():
    """Непрерывный парсинг: каждый цикл в отдельном процессе, при таймауте процесс убивается."""
    cycle_number = 0
    logging.info("=== Парсер запущен: непрерывный режим (цикл в подпроцессе) ===")
    logging.info("Интервал между циклами: %s сек (%s мин)", PARSE_INTERVAL, PARSE_INTERVAL // 60)
    logging.info("Макс. время цикла: %s мин (при превышении процесс убивается)", MAX_CYCLE_TIME // 60)

    while True:
        cycle_number += 1
        cycle_start = asyncio.get_event_loop().time()
        logging.info("=== Начало цикла парсинга #%s ===", cycle_number)
        try:
            await run_one_cycle_subprocess()
            duration = asyncio.get_event_loop().time() - cycle_start
            logging.info("=== Цикл парсинга #%s завершен успешно за %.1f сек ===", cycle_number, duration)
        except asyncio.TimeoutError:
            duration = asyncio.get_event_loop().time() - cycle_start
            logging.error(
                "Цикл парсинга #%s превысил %s мин и был прерван (процесс убит) после %.1f сек.",
                cycle_number, MAX_CYCLE_TIME // 60, duration,
            )
        except Exception as e:
            duration = asyncio.get_event_loop().time() - cycle_start
            logging.error("Ошибка в цикле парсинга #%s после %.1f сек: %s", cycle_number, duration, e, exc_info=True)

        logging.info("Пауза %s сек (%s мин) перед следующим циклом...", PARSE_INTERVAL, PARSE_INTERVAL // 60)
        try:
            await asyncio.sleep(PARSE_INTERVAL)
        except Exception as e:
            logging.error("Ошибка при ожидании: %s", e, exc_info=True)
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(cron())
