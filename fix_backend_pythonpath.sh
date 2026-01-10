#!/bin/bash
# Исправление PYTHONPATH для backend

cd /root/rentsense

echo "=========================================="
echo "ИСПРАВЛЕНИЕ BACKEND PYTHONPATH"
echo "=========================================="

echo ""
echo "1. Остановка backend:"
docker-compose -f docker-compose.prod.yml down backend

echo ""
echo "2. Проверка docker-compose.prod.yml на наличие PYTHONPATH:"
grep -A 2 "PYTHONPATH" docker-compose.prod.yml || echo "PYTHONPATH не найден в docker-compose.prod.yml"

echo ""
echo "3. Если PYTHONPATH не найден, добавим его вручную или обновим файл"
echo "   (Файл должен быть обновлен на сервере с PYTHONPATH: /app)"

echo ""
echo "4. Удаление старого контейнера:"
docker-compose -f docker-compose.prod.yml rm -f backend

echo ""
echo "5. Пересоздание и запуск backend:"
docker-compose -f docker-compose.prod.yml up -d backend

echo ""
echo "6. Ожидание запуска (10 секунд)..."
sleep 10

echo ""
echo "7. Проверка статуса:"
docker-compose -f docker-compose.prod.yml ps backend

echo ""
echo "8. Проверка логов:"
docker-compose -f docker-compose.prod.yml logs backend | tail -20

echo ""
echo "=========================================="

