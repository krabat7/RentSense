import asyncio
from app.api.main import fastapi


async def main():
    """Точка входа: uvicorn для app.api.main.fastapi."""
    await fastapi()


if __name__ == "__main__":
    asyncio.run(main())
