#!/bin/bash
# Диагностика проблем на сервере

cd /root/rentsense

echo "=========================================="
echo "ДИАГНОСТИКА СЕРВЕРА"
echo "=========================================="

echo ""
echo "1. Статус контейнеров:"
docker-compose -f docker-compose.prod.yml ps -a

echo ""
echo "2. Логи MySQL (последние 100 строк):"
docker-compose -f docker-compose.prod.yml logs mysql 2>&1 | tail -100

echo ""
echo "3. Проверка .env файла:"
if [ -f .env ]; then
    echo ".env существует"
    echo "DB переменные:"
    grep -E "^DB_|^MYSQL_" .env | sed 's/\(PASSWORD\|PASS\)=.*/\1=***/' || echo "DB переменные не найдены"
else
    echo "ERROR: .env файл не найден!"
fi

echo ""
echo "4. Проверка docker-compose.prod.yml:"
if [ -f docker-compose.prod.yml ]; then
    echo "docker-compose.prod.yml существует"
    echo "Healthcheck для backend:"
    grep -A 6 "backend:" docker-compose.prod.yml | grep -A 5 "healthcheck:" || echo "Healthcheck не найден (уже отключен?)"
else
    echo "ERROR: docker-compose.prod.yml не найден!"
fi

echo ""
echo "5. Дисковое пространство:"
df -h

echo ""
echo "6. Docker volumes:"
docker volume ls | grep -E "rentsense|mysql" || echo "Volumes не найдены"

echo ""
echo "7. Проверка портов:"
netstat -tuln | grep -E "3306|8000" || ss -tuln | grep -E "3306|8000"

echo ""
echo "=========================================="

