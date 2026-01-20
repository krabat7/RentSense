import asyncio
from app.api.main import fastapi


async def main():
    """Запуск FastAPI сервера."""
    await fastapi()


if __name__ == "__main__":
    asyncio.run(main())
