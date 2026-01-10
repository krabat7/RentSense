#!/bin/bash
# Проверка статуса сервисов на сервере

cd /root/rentsense

echo "=== Статус всех контейнеров ==="
docker-compose -f docker-compose.prod.yml ps -a

echo ""
echo "=== Логи MySQL (последние 50 строк) ==="
docker-compose -f docker-compose.prod.yml logs --tail=50 mysql

echo ""
echo "=== Логи backend (если есть) ==="
docker-compose -f docker-compose.prod.yml logs --tail=30 backend 2>&1

echo ""
echo "=== Проверка .env файла ==="
if [ -f .env ]; then
    echo ".env существует"
    grep -E "^DB_|^MYSQL_" .env | sed 's/\(PASSWORD\|PASS\)=.*/\1=***/' || echo "DB переменные не найдены"
else
    echo "ERROR: .env файл не найден!"
fi

echo ""
echo "=== Проверка docker-compose.prod.yml (healthcheck) ==="
grep -A 5 "healthcheck:" docker-compose.prod.yml | head -10 || echo "healthcheck не найден"

echo ""
echo "=== Использование дискового пространства ==="
df -h

echo ""
echo "=== Проверка Docker volumes ==="
docker volume ls | grep rentsense || echo "Volumes не найдены"

