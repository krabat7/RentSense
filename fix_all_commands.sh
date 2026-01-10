#!/bin/bash

cd /root/rentsense

echo "=== ШАГ 1: Исправление docker-compose.prod.yml (удаление дублирующего healthcheck) ==="

# Удалить первый healthcheck (строки 594-599) и оставить только второй
sed -i '/healthcheck:/,/start_period: 120s/{ /test: \["CMD-SHELL", "ps aux | grep -q/,$d; }' docker-compose.prod.yml
sed -i '/healthcheck:/N; /test: \["CMD-SHELL", "ps aux | grep -q/,$d' docker-compose.prod.yml || true

# Более точный способ - удалить строки с первым healthcheck
sed -i '594,599d' docker-compose.prod.yml 2>/dev/null || {
    # Если номера строк другие, удалить через grep
    python3 << 'EOF'
import re

with open('docker-compose.prod.yml', 'r') as f:
    content = f.read()

# Удалить первый healthcheck (CMD-SHELL с ps aux)
pattern = r'    healthcheck:\s+test: \["CMD-SHELL", "ps aux.*?start_period: 120s\s+'
content = re.sub(pattern, '', content, flags=re.DOTALL)

with open('docker-compose.prod.yml', 'w') as f:
    f.write(content)
EOF
}

echo "✓ docker-compose.prod.yml исправлен"

echo ""
echo "=== ШАГ 2: Исправление app/scheduler/tasks.py (вернуть синхронный подход) ==="

cat > app/scheduler/tasks.py << 'EOF'
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
EOF

echo "✓ app/scheduler/tasks.py исправлен"

echo ""
echo "=== ШАГ 3: Обновление app/scheduler/crontab.py ==="

cat > app/scheduler/crontab.py << 'EOF'
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
EOF

echo "✓ app/scheduler/crontab.py обновлен"

echo ""
echo "=== ШАГ 4: Обновление requirements.txt ==="

# Добавить nest_asyncio если его нет
if ! grep -q "nest_asyncio" requirements.txt; then
    sed -i '/^playwright==/a nest_asyncio==1.6.0' requirements.txt
fi

echo "✓ requirements.txt обновлен"

echo ""
echo "=== ШАГ 5: Проверка изменений ==="
echo "docker-compose.prod.yml healthcheck:"
grep -A 5 "healthcheck:" docker-compose.prod.yml | head -10

echo ""
echo "requirements.txt nest_asyncio:"
grep "nest_asyncio" requirements.txt

echo ""
echo "=== ШАГ 6: Пересборка и перезапуск контейнеров ==="

echo "Пересборка parser..."
docker-compose -f docker-compose.prod.yml build parser

echo "Перезапуск parser..."
docker-compose -f docker-compose.prod.yml up -d parser

echo "Перезапуск backend..."
docker-compose -f docker-compose.prod.yml up -d --force-recreate backend

echo "Ожидание 20 секунд..."
sleep 20

echo ""
echo "=== ШАГ 7: Проверка статуса ==="
docker-compose -f docker-compose.prod.yml ps

echo ""
echo "=== ШАГ 8: Проверка логов parser (последние 50 строк) ==="
docker-compose -f docker-compose.prod.yml logs parser | tail -50

echo ""
echo "=== ГОТОВО! ==="

