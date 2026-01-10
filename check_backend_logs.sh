#!/bin/bash
# Проверка логов backend

cd /root/rentsense

echo "=== Проверка статуса контейнеров ==="
docker-compose -f docker-compose.prod.yml ps

echo ""
echo "=== Логи backend (последние 50 строк) ==="
docker-compose -f docker-compose.prod.yml logs --tail=50 backend

echo ""
echo "=== Проверка доступности health endpoint ==="
docker-compose -f docker-compose.prod.yml exec backend curl -f http://localhost:8000/health || echo "Health endpoint недоступен"

echo ""
echo "=== Проверка запущен ли процесс Python ==="
docker-compose -f docker-compose.prod.yml exec backend ps aux | grep python || echo "Python процесс не найден"

