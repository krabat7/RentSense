import asyncio
from functools import wraps


def to_thread(func, *args, **kwargs):
    """
    Выполнить sync-функцию в пуле потоков.
    Вызов: await to_thread(func, *args, **kwargs) или await to_thread(func)(*args, **kwargs).
    asyncio.to_thread не принимает **kwargs, поэтому аргументы передаются через lambda.
    """
    async def _run(f, *a, **k):
        return await asyncio.to_thread(lambda: f(*a, **k))

    if args or kwargs:
        return _run(func, *args, **kwargs)
    @wraps(func)
    async def wrapper(*a, **k):
        return await _run(func, *a, **k)
    return wrapper


