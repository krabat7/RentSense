"""Общие настройки pytest: лимиты запросов API отключены, чтобы тесты не получали 429."""

import os

os.environ["RS_RATE_LIMIT_ENABLED"] = "0"
