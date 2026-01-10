#!/bin/bash
cd /root/rentsense && \
echo "=== ШАГ 1: Исправление docker-compose.prod.yml ===" && \
python3 << 'PYTHON_EOF'
with open('docker-compose.prod.yml', 'r') as f:
    content = f.read()

# Удалить первый healthcheck блок (CMD-SHELL)
lines = content.split('\n')
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    # Если нашли healthcheck с CMD-SHELL, пропустить весь блок
    if 'test: ["CMD-SHELL", "ps aux' in line:
        # Найти начало healthcheck (5 строк назад)
        start_idx = max(0, i - 5)
        found_start = False
        for j in range(start_idx, i + 1):
            if 'healthcheck:' in lines[j]:
                # Удалить от healthcheck: до start_period включительно
                found_start = True
                break
        if found_start:
            # Пропустить строки от healthcheck до start_period
            while i < len(lines) and 'start_period: 120s' not in lines[i]:
                i += 1
            i += 1  # пропустить start_period
            continue
    new_lines.append(line)
    i += 1

with open('docker-compose.prod.yml', 'w') as f:
    f.write('\n'.join(new_lines))

print("✓ docker-compose.prod.yml исправлен")
PYTHON_EOF

echo "=== ШАГ 2: Исправление tasks.py ===" && \
cat > app/scheduler/tasks.py << 'TASKS_EOF'
import asyncio
import logging
from app.parser.main import apartPage, listPages

lock = asyncio.Lock()


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
TASKS_EOF

echo "=== ШАГ 3: Обновление crontab.py ===" && \
cat > app/scheduler/crontab.py << 'CRONTAB_EOF'
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
CRONTAB_EOF

echo "=== ШАГ 4: Обновление requirements.txt ===" && \
if ! grep -q "nest_asyncio" requirements.txt; then sed -i '/^playwright==/a nest_asyncio==1.6.0' requirements.txt; fi && \

echo "=== ШАГ 5: Пересборка и перезапуск ===" && \
docker-compose -f docker-compose.prod.yml build parser && \
docker-compose -f docker-compose.prod.yml up -d parser && \
docker-compose -f docker-compose.prod.yml up -d --force-recreate backend && \
sleep 20 && \

echo "=== ШАГ 6: Проверка статуса ===" && \
docker-compose -f docker-compose.prod.yml ps && \
echo "" && \
echo "=== ШАГ 7: Логи parser ===" && \
docker-compose -f docker-compose.prod.yml logs parser | tail -50

