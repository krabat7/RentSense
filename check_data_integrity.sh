#!/bin/bash
cd /root/rentsense || exit 1

MYSQL_CMD="mysql -uroot -pRentSense2025\!Secure rentsense --default-character-set=utf8mb4"

echo "=== ПРОВЕРКА ЦЕЛОСТНОСТИ ДАННЫХ ==="
echo ""

# 1. Количество записей
echo "1. КОЛИЧЕСТВО ЗАПИСЕЙ:"
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT 'offers' as таблица, COUNT(*) as записей FROM offers
UNION ALL SELECT 'addresses', COUNT(*) FROM addresses
UNION ALL SELECT 'realty_inside', COUNT(*) FROM realty_inside
UNION ALL SELECT 'realty_outside', COUNT(*) FROM realty_outside
UNION ALL SELECT 'realty_details', COUNT(*) FROM realty_details
UNION ALL SELECT 'offers_details', COUNT(*) FROM offers_details
UNION ALL SELECT 'developers', COUNT(*) FROM developers;" 2>/dev/null
echo ""

# 2. Проверка связей
echo "2. ПРОВЕРКА СВЯЗЕЙ (должно быть 0):"
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT 'Без адреса' as проблема, COUNT(*) as количество
FROM offers o LEFT JOIN addresses a ON o.cian_id = a.cian_id WHERE a.cian_id IS NULL
UNION ALL
SELECT 'Без внутренних характеристик', COUNT(*)
FROM offers o LEFT JOIN realty_inside ri ON o.cian_id = ri.cian_id WHERE ri.cian_id IS NULL
UNION ALL
SELECT 'Без внешних характеристик', COUNT(*)
FROM offers o LEFT JOIN realty_outside ro ON o.cian_id = ro.cian_id WHERE ro.cian_id IS NULL
UNION ALL
SELECT 'Без деталей недвижимости', COUNT(*)
FROM offers o LEFT JOIN realty_details rd ON o.cian_id = rd.cian_id WHERE rd.cian_id IS NULL
UNION ALL
SELECT 'Без деталей объявления', COUNT(*)
FROM offers o LEFT JOIN offers_details od ON o.cian_id = od.cian_id WHERE od.cian_id IS NULL
UNION ALL
SELECT 'Без застройщика', COUNT(*)
FROM offers o LEFT JOIN developers d ON o.cian_id = d.cian_id WHERE d.cian_id IS NULL;" 2>/dev/null
echo ""

# 3. Проверка критичных полей
echo "3. ПРОВЕРКА КРИТИЧНЫХ ПОЛЕЙ (должно быть 0):"
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT 'offers: цена NULL' as проблема, COUNT(*) as количество FROM offers WHERE price IS NULL
UNION ALL SELECT 'offers: cian_id NULL', COUNT(*) FROM offers WHERE cian_id IS NULL
UNION ALL SELECT 'addresses: cian_id NULL', COUNT(*) FROM addresses WHERE cian_id IS NULL;" 2>/dev/null
echo ""

# 4. Проверка дубликатов
echo "4. ПРОВЕРКА ДУБЛИКАТОВ (должно быть 0):"
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT 'offers: дубликаты' as проблема, COUNT(*) - COUNT(DISTINCT cian_id) as количество FROM offers
UNION ALL SELECT 'addresses: дубликаты', COUNT(*) - COUNT(DISTINCT cian_id) FROM addresses;" 2>/dev/null
echo ""

# 5. Последние 5 объявлений
echo "5. ПОСЛЕДНИЕ 5 ОБЪЯВЛЕНИЙ (проверка заполненности):"
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT 
    o.cian_id,
    CASE WHEN a.cian_id IS NOT NULL THEN '✓' ELSE '✗' END as адрес,
    CASE WHEN ri.cian_id IS NOT NULL THEN '✓' ELSE '✗' END as внутри,
    CASE WHEN ro.cian_id IS NOT NULL THEN '✓' ELSE '✗' END as снаружи,
    CASE WHEN rd.cian_id IS NOT NULL THEN '✓' ELSE '✗' END as детали,
    CASE WHEN od.cian_id IS NOT NULL THEN '✓' ELSE '✗' END as объявление,
    CASE WHEN d.cian_id IS NOT NULL THEN '✓' ELSE '✗' END as застройщик
FROM offers o
LEFT JOIN addresses a ON o.cian_id = a.cian_id
LEFT JOIN realty_inside ri ON o.cian_id = ri.cian_id
LEFT JOIN realty_outside ro ON o.cian_id = ro.cian_id
LEFT JOIN realty_details rd ON o.cian_id = rd.cian_id
LEFT JOIN offers_details od ON o.cian_id = od.cian_id
LEFT JOIN developers d ON o.cian_id = d.cian_id
ORDER BY o.created_at DESC LIMIT 5;" 2>/dev/null
echo ""

# 6. Статистика заполненности
echo "6. СТАТИСТИКА ЗАПОЛНЕННОСТИ ПОЛЕЙ:"
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT 
    'addresses: district' as поле,
    COUNT(*) as всего,
    SUM(CASE WHEN district IS NOT NULL THEN 1 ELSE 0 END) as заполнено,
    ROUND(SUM(CASE WHEN district IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as '%'
FROM addresses
UNION ALL
SELECT 'realty_inside: rooms_count', COUNT(*), SUM(CASE WHEN rooms_count IS NOT NULL THEN 1 ELSE 0 END), ROUND(SUM(CASE WHEN rooms_count IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
FROM realty_inside
UNION ALL
SELECT 'realty_inside: total_area', COUNT(*), SUM(CASE WHEN total_area IS NOT NULL THEN 1 ELSE 0 END), ROUND(SUM(CASE WHEN total_area IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
FROM realty_inside
UNION ALL
SELECT 'realty_outside: build_year', COUNT(*), SUM(CASE WHEN build_year IS NOT NULL THEN 1 ELSE 0 END), ROUND(SUM(CASE WHEN build_year IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
FROM realty_outside;" 2>/dev/null
echo ""

# 7. Итоговый отчет
echo "7. ИТОГОВЫЙ ОТЧЕТ:"
TOTAL=$(docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "SELECT COUNT(*) FROM offers;" 2>/dev/null | tail -1 | tr -d ' ')
COMPLETE=$(docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT COUNT(*) FROM offers o
WHERE EXISTS (SELECT 1 FROM addresses a WHERE a.cian_id = o.cian_id)
AND EXISTS (SELECT 1 FROM realty_inside ri WHERE ri.cian_id = o.cian_id)
AND EXISTS (SELECT 1 FROM realty_outside ro WHERE ro.cian_id = o.cian_id)
AND EXISTS (SELECT 1 FROM realty_details rd WHERE rd.cian_id = o.cian_id)
AND EXISTS (SELECT 1 FROM offers_details od WHERE od.cian_id = o.cian_id)
AND EXISTS (SELECT 1 FROM developers d WHERE d.cian_id = o.cian_id);" 2>/dev/null | tail -1 | tr -d ' ')

if [ -n "$TOTAL" ] && [ "$TOTAL" -gt 0 ]; then
    PERCENT=$(echo "scale=1; $COMPLETE * 100 / $TOTAL" | bc)
    echo "Всего объявлений: $TOTAL"
    echo "Полностью заполненных: $COMPLETE ($PERCENT%)"
    if [ "$COMPLETE" -eq "$TOTAL" ]; then
        echo "✓ ВСЕ ОБЪЯВЛЕНИЯ ПОЛНОСТЬЮ ЗАПОЛНЕНЫ!"
    fi
fi
