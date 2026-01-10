# Финальное исправление проблем на сервере

## Проблема 1: Два healthcheck в docker-compose.prod.yml

В `docker-compose.prod.yml` есть два healthcheck для backend (строки 594-599 и 602-607). Нужно удалить первый (строки 594-599).

## Проблема 2: Playwright Sync API внутри asyncio loop

`nest_asyncio` не всегда помогает. Лучше использовать подход из `ocenomet` - обернуть весь блок в `asyncio.to_thread` вместо отдельных функций.

## Решение на сервере:

### ШАГ 1: Исправить docker-compose.prod.yml

```bash
cd /root/rentsense
nano docker-compose.prod.yml
```

**Найти и удалить первый healthcheck (строки 594-599):**
```yaml
    healthcheck:
       test: ["CMD-SHELL", "ps aux | grep -q '[p]ython.*app/main.py' || exit 1"]
       interval: 30s
       timeout: 10s
       retries: 5
       start_period: 120s
```

**Оставить только второй healthcheck (строки 602-607).**

### ШАГ 2: Обновить requirements.txt

```bash
nano requirements.txt
```

**Найти строку `playwright==1.40.0` и добавить после неё:**
```
nest_asyncio==1.6.0
```

### ШАГ 3: Исправить app/scheduler/crontab.py

```bash
nano app/scheduler/crontab.py
```

**В начале файла (после импортов) добавить:**
```python
import nest_asyncio
nest_asyncio.apply()
```

**Полный файл должен быть:**
```python
import asyncio
import nest_asyncio
from aiocron import crontab
from .tasks import parsing

# Разрешить вложенные event loops для Playwright
nest_asyncio.apply()


async def cron():
    crontab('0 0 * * *', func=parsing)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(cron())
```

### ШАГ 4: Исправить app/scheduler/tasks.py (альтернативный подход)

Если `nest_asyncio` не поможет, использовать подход из ocenomet - обернуть весь блок:

```bash
nano app/scheduler/tasks.py
```

**Заменить функцию `parsing` на:**
```python
async def parsing(page=1):
    rooms = ['', 'room1', 'room2', 'room3', 'room4', 'room5', 'room6', 'room7', 'room8', 'room9']
    sorts = ['', 'creation_date_asc', 'creation_date_desc']

    def process_page(page, sort, room):
        errors = 0
        while errors < 30:
            pglist = listPages(page, sort, room)
            if pglist == 'END':
                logging.info('End of pglist reached')
                break
            data = apartPage(pglist)
            if data == 'END':
                logging.info('End of data reached')
                break
            if not data:
                errors += 1
                logging.info(f'Error parse count: {errors}')
                if errors >= 30:
                    logging.info(f'Error limit {errors} reached')
                    break
            else:
                errors = 0
            page += 1
        logging.info(f'Page: {page}\nRooms: {room}\nSort: {sort}\nEND')

    def theard():
        for room in rooms:
            for sort in sorts:
                process_page(page, sort, room)
                logging.info(f'Finished: Rooms: {room}, Sort: {sort}')

    async with lock:
        await asyncio.to_thread(theard)
```

**Важно:** Вернуть синхронные функции и обернуть только `theard()` в `asyncio.to_thread`, как в оригинале.

### ШАГ 5: Переустановить зависимости и перезапустить

```bash
cd /root/rentsense

# Пересобрать parser контейнер с новыми зависимостями
docker-compose -f docker-compose.prod.yml build parser

# Перезапустить parser
docker-compose -f docker-compose.prod.yml up -d parser

# Перезапустить backend
docker-compose -f docker-compose.prod.yml up -d --force-recreate backend

# Подождать
sleep 20

# Проверить статус
docker-compose -f docker-compose.prod.yml ps

# Проверить логи parser (не должно быть ошибок Playwright)
docker-compose -f docker-compose.prod.yml logs parser | tail -50
```

