"""
Один цикл парсинга в отдельном процессе.
Запуск: python -m app.scheduler.run_parser_once
При убийстве процесса (таймаут в crontab) ОС освобождает браузер и ресурсы.
"""
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main():
    from app.parser.main import close_browser
    from app.scheduler.tasks import run_one_cycle_sync

    try:
        run_one_cycle_sync()
    finally:
        try:
            close_browser()
        except Exception as e:
            logging.warning("close_browser: %s", e)
    sys.exit(0)


if __name__ == "__main__":
    main()
