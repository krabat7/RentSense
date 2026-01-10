#!/bin/bash
# Инициализация схемы БД на сервере

cd /root/rentsense

echo "=========================================="
echo "ИНИЦИАЛИЗАЦИЯ СХЕМЫ БД"
echo "=========================================="

echo ""
echo "1. Проверка подключения к MySQL:"
docker-compose -f docker-compose.prod.yml exec mysql mysql -uroot -pRentSense2025\!Secure -e "SELECT DATABASE();" rentsense

echo ""
echo "2. Проверка существующих таблиц (до инициализации):"
docker-compose -f docker-compose.prod.yml exec mysql mysql -uroot -pRentSense2025\!Secure -e "USE rentsense; SHOW TABLES;" || echo "Таблиц нет"

echo ""
echo "3. Инициализация схемы БД:"
docker-compose -f docker-compose.prod.yml run --rm backend python app/parser/init_db.py

echo ""
echo "4. Проверка созданных таблиц:"
docker-compose -f docker-compose.prod.yml exec mysql mysql -uroot -pRentSense2025\!Secure -e "USE rentsense; SHOW TABLES;"

echo ""
echo "5. Проверка структуры таблиц:"
docker-compose -f docker-compose.prod.yml exec mysql mysql -uroot -pRentSense2025\!Secure -e "USE rentsense; DESCRIBE offers;" | head -20

echo ""
echo "=========================================="
echo "ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА"
echo "=========================================="

