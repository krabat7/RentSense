#!/bin/bash
cd /root/rentsense || exit 1

MYSQL_CMD="mysql -uroot -pRentSense2025\!Secure rentsense --default-character-set=utf8mb4"

echo "=== СТАТИСТИКА ПАРСИНГА ==="
echo "Время: $(date)"
echo ""

# 1. Общее количество
echo "1. ОБЩЕЕ КОЛИЧЕСТВО ЗАПИСЕЙ:"
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "SELECT 'offers' as table_name, COUNT(*) as rows FROM offers;" 2>/dev/null
echo ""

# 2. За последние 2 часа
echo "2. ЗА ПОСЛЕДНИЕ 2 ЧАСА:"
TWO_HOUR=$(docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "SELECT COUNT(*) FROM offers WHERE created_at >= DATE_SUB(NOW(), INTERVAL 2 HOUR);" 2>/dev/null | tail -1 | tr -d ' ')
echo "  Добавлено: $TWO_HOUR объявлений"
if [ -n "$TWO_HOUR" ] && [ "$TWO_HOUR" -gt 0 ]; then
    SPEED=$(echo "scale=1; $TWO_HOUR / 2" | bc 2>/dev/null || echo "0")
    echo "  Скорость: ~$SPEED объявлений/час"
fi
echo ""

# 3. За последний час
echo "3. ЗА ПОСЛЕДНИЙ ЧАС:"
ONE_HOUR=$(docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "SELECT COUNT(*) FROM offers WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR);" 2>/dev/null | tail -1 | tr -d ' ')
echo "  Добавлено: $ONE_HOUR объявлений"
echo "  Скорость: ~$ONE_HOUR объявлений/час"
echo ""

# 4. Детальная статистика по часам
echo "4. ДЕТАЛЬНАЯ СТАТИСТИКА ПО ЧАСАМ (последние 2 часа):"
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "SELECT DATE_FORMAT(created_at, '%Y-%m-%d %H:00') as hour, COUNT(*) as added FROM offers WHERE created_at >= DATE_SUB(NOW(), INTERVAL 2 HOUR) GROUP BY DATE_FORMAT(created_at, '%Y-%m-%d %H:00') ORDER BY hour DESC;" 2>/dev/null
echo ""

# 5. Статистика по датам
echo "5. СТАТИСТИКА ПО ДАТАМ (последние 5 дней):"
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "SELECT DATE(created_at) as date, COUNT(*) as added, ROUND(COUNT(*) / 24.0, 1) as per_hour FROM offers WHERE created_at >= DATE_SUB(NOW(), INTERVAL 5 DAY) GROUP BY DATE(created_at) ORDER BY date DESC;" 2>/dev/null
echo ""

# 6. Последние добавленные
echo "6. ПОСЛЕДНИЕ 10 ОБЪЯВЛЕНИЙ:"
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "SELECT cian_id, CONCAT(price, ' руб.') as price, DATE_FORMAT(created_at, '%H:%i:%s') as time FROM offers ORDER BY created_at DESC LIMIT 10;" 2>/dev/null
echo ""

# 7. Итог
echo "7. ИТОГОВАЯ ОЦЕНКА:"
if [ -n "$TWO_HOUR" ] && [ "$TWO_HOUR" -gt 0 ]; then
    AVG=$(echo "scale=1; $TWO_HOUR / 2" | bc 2>/dev/null || echo "0")
    echo "Средняя скорость за 2 часа: ~$AVG объявлений/час"
    if (( $(echo "$AVG >= 20" | bc -l 2>/dev/null || echo "0") )); then
        echo "✓ Скорость хорошая!"
    elif (( $(echo "$AVG >= 10" | bc -l 2>/dev/null || echo "0") )); then
        echo "⚠ Скорость средняя"
    else
        echo "⚠ Скорость низкая"
    fi
fi
