#!/bin/bash
# Очистка Docker для освобождения места

echo "=== Очистка Docker ==="

echo "1. Проверка свободного места..."
df -h /

echo ""
echo "2. Остановка контейнеров..."
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true

echo ""
echo "3. Удаление остановленных контейнеров..."
docker container prune -f

echo ""
echo "4. Удаление неиспользуемых образов..."
docker image prune -a -f

echo ""
echo "5. Удаление неиспользуемых volumes..."
docker volume prune -f

echo ""
echo "6. Очистка build cache..."
docker builder prune -a -f

echo ""
echo "7. Проверка свободного места после очистки..."
df -h /

echo ""
echo "=== Очистка завершена ==="

