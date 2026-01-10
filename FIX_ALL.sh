cd /root/rentsense && \
echo "=== ШАГ 1: Исправление docker-compose.prod.yml ===" && \
cp docker-compose.prod.yml docker-compose.prod.yml.bak && \
sed -i '/test: \["CMD-SHELL", "ps aux/,/start_period: 120s/d' docker-compose.prod.yml && \
sed -i '/healthcheck:/{N;/test: \["CMD-SHELL", "ps aux/{:a;N;/start_period: 120s/!ba;d;}}' docker-compose.prod.yml && \
python3 << 'EOF'
with open('docker-compose.prod.yml', 'r') as f:
    lines = f.readlines()
new_lines = []
i = 0
while i < len(lines):
    if 'test: ["CMD-SHELL", "ps aux' in lines[i]:
        # Найти начало healthcheck (до 5 строк назад)
        start = max(0, i-5)
        for j in range(start, i):
            if 'healthcheck:' in lines[j]:
                # Удалить блок от healthcheck: до start_period: 120s
                i = j
                while i < len(lines) and 'start_period: 120s' not in lines[i]:
                    i += 1
                i += 1
                break
        if j < i:
            continue
    new_lines.append(lines[i])
    i += 1
with open('docker-compose.prod.yml', 'w') as f:
    f.writelines(new_lines)
print('✓ docker-compose.prod.yml исправлен')
EOF && \
echo "=== ШАГ 2: Исправление tasks.py ===" && \
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
echo "✓ tasks.py исправлен" && \
echo "=== ШАГ 3: Обновление crontab.py ===" && \
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
echo "✓ crontab.py обновлен" && \
echo "=== ШАГ 4: Обновление requirements.txt ===" && \
grep -q "nest_asyncio" requirements.txt || sed -i '/^playwright==/a nest_asyncio==1.6.0' requirements.txt && \
echo "✓ requirements.txt обновлен" && \
echo "=== ШАГ 5: Пересборка parser ===" && \
docker-compose -f docker-compose.prod.yml build parser && \
echo "=== ШАГ 6: Перезапуск сервисов ===" && \
docker-compose -f docker-compose.prod.yml up -d parser && \
docker-compose -f docker-compose.prod.yml up -d --force-recreate backend && \
sleep 20 && \
echo "=== ШАГ 7: Проверка статуса ===" && \
docker-compose -f docker-compose.prod.yml ps && \
echo "" && \
echo "=== ШАГ 8: Логи parser (последние 50 строк) ===" && \
docker-compose -f docker-compose.prod.yml logs parser | tail -50

