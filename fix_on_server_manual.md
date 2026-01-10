# Инструкции для ручного исправления на сервере

## Проблема 1: Backend healthcheck показывает unhealthy

### Решение: Проверить, что healthcheck добавлен

```bash
cd /root/rentsense

# Проверить, есть ли healthcheck в docker-compose.prod.yml
grep -A 5 "healthcheck" docker-compose.prod.yml

# Если healthcheck нет, добавить вручную через nano:
nano docker-compose.prod.yml
```

**Найти секцию backend (после строки `ports:`) и добавить:**
```yaml
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 40s
    command: python app/main.py
```

**Сохранить:** `Ctrl+O`, `Enter`, `Ctrl+X`

**Перезапустить backend:**
```bash
docker-compose -f docker-compose.prod.yml up -d --force-recreate backend
sleep 60
docker-compose -f docker-compose.prod.yml ps backend
```

---

## Проблема 2: Playwright Sync API внутри asyncio loop (КРИТИЧНО)

### Проблема: 
Parser вызывает Playwright sync API (`sync_playwright`) из async функции, что недопустимо.

### Решение: Обернуть вызовы в `asyncio.to_thread`

Нужно изменить `app/scheduler/tasks.py` - функция `parsing` должна вызывать синхронные функции через `asyncio.to_thread`.

**Текущий код (строка 15):**
```python
pglist = listPages(page, sort, room)
```

**Исправить на:**
```python
pglist = await asyncio.to_thread(listPages, page, sort, room)
```

**И строку 19:**
```python
data = apartPage(pglist)
```

**Исправить на:**
```python
data = await asyncio.to_thread(apartPage, pglist)
```

### Команды на сервере:

```bash
cd /root/rentsense

# Открыть файл для редактирования
nano app/scheduler/tasks.py
```

**Найти функцию `process_page` (примерно строка 12-32) и изменить:**

**Было:**
```python
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
        # ... остальной код
```

**Стало (async функция):**
```python
async def process_page(page, sort, room):
    errors = 0
    while errors < 30:
        pglist = await asyncio.to_thread(listPages, page, sort, room)
        if pglist == 'END':
            logging.info('End of pglist reached')
            break
        data = await asyncio.to_thread(apartPage, pglist)
        if data == 'END':
            logging.info('End of data reached')
            break
        # ... остальной код
```

**И в функции `theard()` изменить вызов:**
```python
async def theard():
    for room in rooms:
        for sort in sorts:
            await process_page(page, sort, room)
            logging.info(f'Finished: Rooms: {room}, Sort: {sort}')
```

**И в функции `parsing` убрать `asyncio.to_thread` из вызова `theard()`:**
```python
async def parsing(page=1):
    # ... код ...
    
    async with lock:
        await theard()  # убрать asyncio.to_thread
```

**Сохранить:** `Ctrl+O`, `Enter`, `Ctrl+X`

**Перезапустить parser:**
```bash
docker-compose -f docker-compose.prod.yml restart parser
sleep 10
docker-compose -f docker-compose.prod.yml logs parser | tail -30
```

---

## Альтернатива: Исправить файлы локально и скопировать

**На локальном компьютере (PowerShell) можно попробовать:**
```powershell
cd F:\hw_hse\Diploma\RentSense

# Исправить файлы локально (я это сделаю)

# Затем скопировать через SSH с ключом или вручную
# Или использовать FileZilla/WinSCP для графического копирования
```

