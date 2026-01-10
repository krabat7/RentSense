#!/bin/bash
# Исправление MySQL: удаление поврежденного volume и создание новой БД

cd /root/rentsense

echo "=========================================="
echo "ИСПРАВЛЕНИЕ MYSQL"
echo "=========================================="

echo ""
echo "1. Остановка MySQL:"
docker-compose -f docker-compose.prod.yml down

echo ""
echo "2. Удаление поврежденного volume:"
docker volume ls | grep mysql
docker volume rm rentsense_mysql_data || echo "Volume не найден (уже удален?)"

echo ""
echo "3. Очистка всех MySQL volumes:"
docker volume ls | grep -E "mysql|rentsense" | awk '{print $2}' | xargs -r docker volume rm || echo "Volumes не найдены"

echo ""
echo "4. Запуск MySQL с новым чистым volume:"
docker-compose -f docker-compose.prod.yml up -d mysql

echo ""
echo "5. Ожидание инициализации MySQL (30 секунд)..."
sleep 30

echo ""
echo "6. Проверка статуса:"
docker-compose -f docker-compose.prod.yml ps -a

echo ""
echo "7. Логи MySQL:"
docker-compose -f docker-compose.prod.yml logs mysql | tail -30

echo ""
echo "8. Если MySQL запустился успешно, проверить подключение:"
echo "   docker-compose -f docker-compose.prod.yml exec mysql mysql -uroot -pRentSense2025\!Secure -e 'SELECT 1;'"

echo ""
echo "=========================================="

