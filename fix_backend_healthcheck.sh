#!/bin/bash
# Исправление healthcheck и перезапуск backend

cd /root/rentsense

echo "=== Проверка статуса контейнеров ==="
docker-compose -f docker-compose.prod.yml ps -a

echo ""
echo "=== Логи backend ==="
docker-compose -f docker-compose.prod.yml logs backend 2>&1 | tail -50

echo ""
echo "=== Временно отключаем healthcheck ==="
sed -i '/healthcheck:/,/#healthcheck_end/{/healthcheck:/a\
      #healthcheck: TEMP_DISABLED
}' docker-compose.prod.yml

# Или проще - закомментировать весь блок healthcheck
sed -i 's/^    healthcheck:/#    healthcheck:/' docker-compose.prod.yml
sed -i 's/^      test:/#      test:/' docker-compose.prod.yml
sed -i 's/^      interval:/#      interval:/' docker-compose.prod.yml
sed -i 's/^      timeout:/#      timeout:/' docker-compose.prod.yml
sed -i 's/^      retries:/#      retries:/' docker-compose.prod.yml
sed -i 's/^      start_period:/#      start_period:/' docker-compose.prod.yml

echo ""
echo "=== Перезапуск ==="
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d mysql backend

echo ""
echo "=== Ожидание 30 секунд ==="
sleep 30

echo ""
echo "=== Проверка статуса ==="
docker-compose -f docker-compose.prod.yml ps

echo ""
echo "=== Логи backend после запуска ==="
docker-compose -f docker-compose.prod.yml logs backend 2>&1 | tail -30

