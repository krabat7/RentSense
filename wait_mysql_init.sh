#!/bin/bash
# Ожидание завершения инициализации MySQL

cd /root/rentsense

echo "=========================================="
echo "ОЖИДАНИЕ ИНИЦИАЛИЗАЦИИ MYSQL"
echo "=========================================="

echo ""
echo "Подождите 60 секунд для завершения инициализации..."
sleep 60

echo ""
echo "1. Проверка статуса:"
docker-compose -f docker-compose.prod.yml ps -a

echo ""
echo "2. Последние логи MySQL:"
docker-compose -f docker-compose.prod.yml logs mysql | tail -50

echo ""
echo "3. Проверка healthcheck:"
docker inspect rentsense_mysql_1 | grep -A 10 "Health" | head -15

echo ""
echo "4. Попытка подключения БЕЗ пароля (первый запуск):"
docker-compose -f docker-compose.prod.yml exec mysql mysql -uroot -e "SELECT 1 as test;" 2>&1 || echo "Подключение без пароля не удалось"

echo ""
echo "5. Попытка подключения С паролем:"
docker-compose -f docker-compose.prod.yml exec mysql mysql -uroot -pRentSense2025\!Secure -e "SELECT 1 as test;" 2>&1 || echo "Подключение с паролем не удалось"

echo ""
echo "6. Проверка базы данных:"
docker-compose -f docker-compose.prod.yml exec mysql mysql -uroot -pRentSense2025\!Secure -e "SHOW DATABASES;" 2>&1 || echo "Не удалось проверить базы данных"

echo ""
echo "=========================================="

