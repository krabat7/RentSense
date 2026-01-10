#!/bin/bash
cd /root/rentsense || exit 1

echo "=== СТАТИСТИКА ПАРСИНГА ==="
echo "Время: $(date)"
echo ""

# 1. Общее количество
echo "1. ОБЩЕЕ КОЛИЧЕСТВО ЗАПИСЕЙ:"
TOTAL=$(docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT COUNT(*) FROM offers;" 2>/dev/null | tail -1 | tr -d ' ')
echo "  Всего объявлений: $TOTAL"
echo ""

# 2. За последние 2 часа
echo "2. ЗА ПОСЛЕДНИЕ 2 ЧАСА:"
TWO_HOUR=$(docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT COUNT(*) FROM offers WHERE created_at >= DATE_SUB(NOW(), INTERVAL 2 HOUR);" 2>/dev/null | tail -1 | tr -d ' ')
echo "  Добавлено: $TWO_HOUR объявлений"
if [ -n "$TWO_HOUR" ] && [ "$TWO_HOUR" != "count" ] && [ "$TWO_HOUR" -gt 0 ] 2>/dev/null; then
    SPEED=$(echo "scale=1; $TWO_HOUR / 2" | bc 2>/dev/null || echo "0")
    echo "  Скорость: ~$SPEED объявлений/час"
else
    echo "  Скорость: недостаточно данных"
fi
echo ""

# 3. За последний час
echo "3. ЗА ПОСЛЕДНИЙ ЧАС:"
ONE_HOUR=$(docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT COUNT(*) FROM offers WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR);" 2>/dev/null | tail -1 | tr -d ' ')
echo "  Добавлено: $ONE_HOUR объявлений"
if [ -n "$ONE_HOUR" ] && [ "$ONE_HOUR" != "count" ] && [ "$ONE_HOUR" -gt 0 ] 2>/dev/null; then
    echo "  Скорость: ~$ONE_HOUR объявлений/час"
else
    echo "  Скорость: недостаточно данных"
fi
echo ""

# 4. Детальная статистика по часам
echo "4. ДЕТАЛЬНАЯ СТАТИСТИКА ПО ЧАСАМ:"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT DATE_FORMAT(created_at, '%H:00') as hour, COUNT(*) as added FROM offers WHERE created_at >= DATE_SUB(NOW(), INTERVAL 2 HOUR) GROUP BY DATE_FORMAT(created_at, '%Y-%m-%d %H:00') ORDER BY hour DESC;" 2>/dev/null
echo ""

# 5. Статистика по датам
echo "5. СТАТИСТИКА ПО ДАТАМ (последние 5 дней):"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT DATE(created_at) as date, COUNT(*) as added, ROUND(COUNT(*) / 24.0, 1) as per_hour FROM offers WHERE created_at >= DATE_SUB(NOW(), INTERVAL 5 DAY) GROUP BY DATE(created_at) ORDER BY date DESC;" 2>/dev/null
echo ""

# 6. Последние добавленные
echo "6. ПОСЛЕДНИЕ 10 ОБЪЯВЛЕНИЙ:"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT cian_id, price, DATE_FORMAT(created_at, '%H:%i:%s') as time FROM offers ORDER BY created_at DESC LIMIT 10;" 2>/dev/null
echo ""

# 7. Итог
echo "7. ИТОГОВАЯ ОЦЕНКА:"
if [ -n "$TWO_HOUR" ] && [ "$TWO_HOUR" != "count" ] && [ "$TWO_HOUR" -gt 0 ] 2>/dev/null; then
    AVG=$(echo "scale=1; $TWO_HOUR / 2" | bc 2>/dev/null || echo "0")
    echo "Средняя скорость за 2 часа: ~$AVG объявлений/час"
    if (( $(echo "$AVG >= 20" | bc -l 2>/dev/null || echo "0") )); then
        echo "✓ Скорость хорошая! (>=20 объявлений/час)"
    elif (( $(echo "$AVG >= 10" | bc -l 2>/dev/null || echo "0") )); then
        echo "⚠ Скорость средняя (10-20 объявлений/час)"
    else
        echo "⚠ Скорость низкая (<10 объявлений/час)"
    fi
else
    echo "⚠ Недостаточно данных за последние 2 часа"
fi
