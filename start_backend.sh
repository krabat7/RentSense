#!/bin/bash
# Запуск backend на сервере

cd /root/rentsense

echo "=========================================="
echo "ЗАПУСК BACKEND"
echo "=========================================="

echo ""
echo "1. Проверка статуса MySQL:"
docker-compose -f docker-compose.prod.yml ps mysql

echo ""
echo "2. Запуск backend:"
docker-compose -f docker-compose.prod.yml up -d backend

echo ""
echo "3. Ожидание запуска backend (10 секунд)..."
sleep 10

echo ""
echo "4. Проверка статуса backend:"
docker-compose -f docker-compose.prod.yml ps backend

echo ""
echo "5. Логи backend:"
docker-compose -f docker-compose.prod.yml logs backend | tail -30

echo ""
echo "6. Проверка health endpoint:"
curl -s http://localhost:8000/health || echo "Health endpoint недоступен"

echo ""
echo "7. Проверка процессов в контейнере:"
docker-compose -f docker-compose.prod.yml exec backend ps aux | grep python || echo "Процессы не найдены"

echo ""
echo "=========================================="

