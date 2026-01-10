import asyncio
from app.api.main import fastapi


async def main():
    # Backend запускает только FastAPI
    # Cron запускается отдельно в parser контейнере
    await fastapi()


if __name__ == "__main__":
    asyncio.run(main())
