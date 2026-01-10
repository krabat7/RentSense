#!/bin/bash
# Проверка статистики парсинга

cd /root/rentsense || exit 1

MYSQL_CMD="mysql -uroot -pRentSense2025\!Secure rentsense --default-character-set=utf8mb4"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          СТАТИСТИКА ПАРСИНГА И БАЗЫ ДАННЫХ                ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Текущее время
echo "Время проверки: $(date)"
echo ""

# 1. Общее количество записей
echo "=== 1. ОБЩЕЕ КОЛИЧЕСТВО ЗАПИСЕЙ ==="
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT 
    'offers' as таблица, COUNT(*) as записей FROM offers
UNION ALL SELECT 'addresses', COUNT(*) FROM addresses
UNION ALL SELECT 'realty_inside', COUNT(*) FROM realty_inside
UNION ALL SELECT 'realty_outside', COUNT(*) FROM realty_outside
UNION ALL SELECT 'realty_details', COUNT(*) FROM realty_details
UNION ALL SELECT 'offers_details', COUNT(*) FROM offers_details
UNION ALL SELECT 'developers', COUNT(*) FROM developers;" 2>/dev/null
echo ""

# 2. Статистика по времени добавления
echo "=== 2. СТАТИСТИКА ПО ВРЕМЕНИ ДОБАВЛЕНИЯ ==="
echo ""

echo "За последний час:"
HOUR_COUNT=$(docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "SELECT COUNT(*) FROM offers WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR);" 2>/dev/null | tail -1 | tr -d ' ')
echo "  Количество: $HOUR_COUNT объявлений"
if [ -n "$HOUR_COUNT" ] && [ "$HOUR_COUNT" -gt 0 ]; then
    echo "  Скорость: ~$HOUR_COUNT объявлений/час"
fi
echo ""

echo "За последние 2 часа:"
TWO_HOUR_COUNT=$(docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "SELECT COUNT(*) FROM offers WHERE created_at >= DATE_SUB(NOW(), INTERVAL 2 HOUR);" 2>/dev/null | tail -1 | tr -d ' ')
echo "  Количество: $TWO_HOUR_COUNT объявлений"
if [ -n "$TWO_HOUR_COUNT" ] && [ "$TWO_HOUR_COUNT" -gt 0 ]; then
    TWO_HOUR_SPEED=$(echo "scale=1; $TWO_HOUR_COUNT / 2" | bc 2>/dev/null || echo "0")
    echo "  Скорость: ~$TWO_HOUR_SPEED объявлений/час"
fi
echo ""

echo "За последние 30 минут:"
HALF_HOUR_COUNT=$(docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "SELECT COUNT(*) FROM offers WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 MINUTE);" 2>/dev/null | tail -1 | tr -d ' ')
echo "  Количество: $HALF_HOUR_COUNT объявлений"
if [ -n "$HALF_HOUR_COUNT" ] && [ "$HALF_HOUR_COUNT" -gt 0 ]; then
    HALF_HOUR_SPEED=$(echo "scale=1; $HALF_HOUR_COUNT * 2" | bc 2>/dev/null || echo "0")
    echo "  Скорость: ~$HALF_HOUR_SPEED объявлений/час"
fi
echo ""

echo "За последние 10 минут:"
TEN_MIN_COUNT=$(docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "SELECT COUNT(*) FROM offers WHERE created_at >= DATE_SUB(NOW(), INTERVAL 10 MINUTE);" 2>/dev/null | tail -1 | tr -d ' ')
echo "  Количество: $TEN_MIN_COUNT объявлений"
if [ -n "$TEN_MIN_COUNT" ] && [ "$TEN_MIN_COUNT" -gt 0 ]; then
    TEN_MIN_SPEED=$(echo "scale=1; $TEN_MIN_COUNT * 6" | bc 2>/dev/null || echo "0")
    echo "  Скорость: ~$TEN_MIN_SPEED объявлений/час"
fi
echo ""

# 3. Детальная статистика по часам (последние 2 часа)
echo "=== 3. ДЕТАЛЬНАЯ СТАТИСТИКА ПО ЧАСАМ (последние 2 часа) ==="
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT 
    DATE_FORMAT(created_at, '%Y-%m-%d %H:00') as час,
    COUNT(*) as добавлено,
    MIN(created_at) as первое,
    MAX(created_at) as последнее
FROM offers 
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 2 HOUR)
GROUP BY DATE_FORMAT(created_at, '%Y-%m-%d %H:00')
ORDER BY час DESC;" 2>/dev/null
echo ""

# 4. Статистика по датам (последние 5 дней)
echo "=== 4. СТАТИСТИКА ПО ДАТАМ (последние 5 дней) ==="
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT 
    DATE(created_at) as дата,
    COUNT(*) as добавлено,
    ROUND(COUNT(*) / 24.0, 1) as среднее_в_час
FROM offers 
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 5 DAY)
GROUP BY DATE(created_at)
ORDER BY дата DESC;" 2>/dev/null
echo ""

# 5. Последние добавленные объявления
echo "=== 5. ПОСЛЕДНИЕ 10 ДОБАВЛЕННЫХ ОБЪЯВЛЕНИЙ ==="
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT 
    cian_id,
    CONCAT(price, ' руб.') as цена,
    DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') as добавлено
FROM offers 
ORDER BY created_at DESC 
LIMIT 10;" 2>/dev/null
echo ""

# 6. Итоговая оценка скорости
echo "=== 6. ИТОГОВАЯ ОЦЕНКА СКОРОСТИ ==="
if [ -n "$TWO_HOUR_COUNT" ] && [ "$TWO_HOUR_COUNT" -gt 0 ]; then
    AVG_SPEED=$(echo "scale=1; $TWO_HOUR_COUNT / 2" | bc 2>/dev/null || echo "0")
    echo "Средняя скорость за последние 2 часа: ~$AVG_SPEED объявлений/час"
    
    if (( $(echo "$AVG_SPEED >= 20" | bc -l 2>/dev/null || echo "0") )); then
        echo "✓ Скорость хорошая! (>=20 объявлений/час)"
    elif (( $(echo "$AVG_SPEED >= 10" | bc -l 2>/dev/null || echo "0") )); then
        echo "⚠ Скорость средняя (10-20 объявлений/час)"
    else
        echo "⚠ Скорость низкая (<10 объявлений/час)"
    fi
else
    echo "⚠ Недостаточно данных за последние 2 часа"
fi
echo ""

echo "=== ПРОВЕРКА ЗАВЕРШЕНА ==="

