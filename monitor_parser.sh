#!/bin/bash
# Скрипт для мониторинга парсера RentSense

cd /root/rentsense || exit 1

echo "=== Статус парсера ==="
docker-compose -f docker-compose.prod.yml ps parser
echo ""

echo "=== Последние 50 строк логов ==="
docker-compose -f docker-compose.prod.yml logs --tail=50 parser
echo ""

echo "=== Статистика за последние 10 минут ==="
docker-compose -f docker-compose.prod.yml logs --since 10m parser | grep -E "(is adding|is updating|failed|blocked|Skipped|Added:|ERROR|WARNING)" | tail -20
echo ""

echo "=== Статистика прокси ==="
docker-compose -f docker-compose.prod.yml logs --since 30m parser | grep -E "(blocked|warning|Proxy.*blocked|unfreeze)" | tail -15
echo ""

echo "=== Последние добавленные объявления ==="
docker-compose -f docker-compose.prod.yml logs --since 30m parser | grep "is adding" | tail -10
echo ""

echo "=== Ошибки и предупреждения ==="
docker-compose -f docker-compose.prod.yml logs --since 30m parser | grep -E "(ERROR|WARNING|failed)" | tail -10

