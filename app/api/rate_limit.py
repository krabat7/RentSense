"""
Мягкое ограничение частоты запросов по IP (sliding window).

Включается по умолчанию. В тестах отключается через RS_RATE_LIMIT_ENABLED=0.
Не затрагивает /health и пути документации OpenAPI.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)


def _truthy_env(key: str, default: str = "1") -> bool:
    return os.getenv(key, default).strip().lower() not in ("0", "false", "no", "off")


def _env_int(key: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(key, str(default))))
    except ValueError:
        return default


def _client_ip(request: Request) -> str:
    xf = request.headers.get("x-forwarded-for")
    if xf:
        return xf.split(",")[0].strip() or "unknown"
    if request.client:
        return request.client.host or "unknown"
    return "unknown"


def _should_skip_path(path: str) -> bool:
    if path == "/health":
        return True
    if path.startswith("/docs") or path.startswith("/redoc"):
        return True
    if path in ("/openapi.json", "/"):
        return True
    return False


_store: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def clear_rate_limit_state() -> None:
    """Сброс счётчиков (для тестов и отладки)."""
    with _lock:
        _store.clear()


def _trim_window(dq: deque[float], now: float, window_sec: float) -> None:
    while dq and now - dq[0] > window_sec:
        dq.popleft()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Отдельные лимиты для дешевых API-запросов и тяжелого /api/getparams."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if not _truthy_env("RS_RATE_LIMIT_ENABLED", "1"):
            return await call_next(request)

        path = request.url.path
        if _should_skip_path(path):
            return await call_next(request)

        if not path.startswith("/api"):
            return await call_next(request)

        window = float(_env_int("RS_RATE_LIMIT_WINDOW_SEC", 60))
        if "getparams" in path:
            limit = _env_int("RS_RATE_LIMIT_GETPARAMS_PER_MINUTE", 45)
        else:
            limit = _env_int("RS_RATE_LIMIT_API_PER_MINUTE", 180)

        ip = _client_ip(request)
        if "getparams" in path:
            bucket = "getparams"
        else:
            bucket = "api"
        key = f"{ip}:{bucket}"

        now = time.monotonic()
        with _lock:
            dq = _store[key]
            _trim_window(dq, now, window)
            if len(dq) >= limit:
                logger.warning("rate_limit: 429 key=%s path=%s", key, path)
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Слишком много запросов. Подождите и повторите попытку.",
                    },
                    headers={"Retry-After": str(int(window))},
                )
            dq.append(now)

        return await call_next(request)


def add_rate_limit_middleware(app):
    app.add_middleware(RateLimitMiddleware)
