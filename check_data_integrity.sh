#!/bin/bash
# Комплексная проверка целостности данных в базе

cd /root/rentsense || exit 1

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     ПРОВЕРКА ЦЕЛОСТНОСТИ ДАННЫХ И КОРРЕКТНОСТИ ЗАПИСИ    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

MYSQL_CMD="mysql -uroot -pRentSense2025\!Secure rentsense --default-character-set=utf8mb4"

# 1. Проверка количества записей в каждой таблице
echo "=== 1. КОЛИЧЕСТВО ЗАПИСЕЙ В КАЖДОЙ ТАБЛИЦЕ ==="
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

# 2. Проверка, что у каждого объявления есть все связанные данные
echo "=== 2. ПРОВЕРКА СВЯЗЕЙ МЕЖДУ ТАБЛИЦАМИ ==="
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT 
    'Объявления БЕЗ адреса' as проблема, COUNT(*) as количество
FROM offers o
LEFT JOIN addresses a ON o.cian_id = a.cian_id
WHERE a.cian_id IS NULL
UNION ALL
SELECT 'Объявления БЕЗ внутренних характеристик', COUNT(*)
FROM offers o
LEFT JOIN realty_inside ri ON o.cian_id = ri.cian_id
WHERE ri.cian_id IS NULL
UNION ALL
SELECT 'Объявления БЕЗ внешних характеристик', COUNT(*)
FROM offers o
LEFT JOIN realty_outside ro ON o.cian_id = ro.cian_id
WHERE ro.cian_id IS NULL
UNION ALL
SELECT 'Объявления БЕЗ деталей недвижимости', COUNT(*)
FROM offers o
LEFT JOIN realty_details rd ON o.cian_id = rd.cian_id
WHERE rd.cian_id IS NULL
UNION ALL
SELECT 'Объявления БЕЗ деталей объявления', COUNT(*)
FROM offers o
LEFT JOIN offers_details od ON o.cian_id = od.cian_id
WHERE od.cian_id IS NULL
UNION ALL
SELECT 'Объявления БЕЗ застройщика', COUNT(*)
FROM offers o
LEFT JOIN developers d ON o.cian_id = d.cian_id
WHERE d.cian_id IS NULL;" 2>/dev/null
echo ""

# 3. Проверка критичных полей на NULL
echo "=== 3. ПРОВЕРКА КРИТИЧНЫХ ПОЛЕЙ НА NULL ==="
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT 
    'offers: цена NULL' as проблема, COUNT(*) as количество
FROM offers WHERE price IS NULL
UNION ALL
SELECT 'offers: cian_id NULL', COUNT(*)
FROM offers WHERE cian_id IS NULL
UNION ALL
SELECT 'addresses: cian_id NULL', COUNT(*)
FROM addresses WHERE cian_id IS NULL
UNION ALL
SELECT 'realty_inside: cian_id NULL', COUNT(*)
FROM realty_inside WHERE cian_id IS NULL
UNION ALL
SELECT 'realty_outside: cian_id NULL', COUNT(*)
FROM realty_outside WHERE cian_id IS NULL
UNION ALL
SELECT 'realty_details: cian_id NULL', COUNT(*)
FROM realty_details WHERE cian_id IS NULL
UNION ALL
SELECT 'offers_details: cian_id NULL', COUNT(*)
FROM offers_details WHERE cian_id IS NULL
UNION ALL
SELECT 'developers: cian_id NULL', COUNT(*)
FROM developers WHERE cian_id IS NULL;" 2>/dev/null
echo ""

# 4. Проверка дубликатов cian_id
echo "=== 4. ПРОВЕРКА ДУБЛИКАТОВ (должно быть 0) ==="
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT 
    'offers: дубликаты cian_id' as проблема, COUNT(*) - COUNT(DISTINCT cian_id) as количество
FROM offers
UNION ALL
SELECT 'addresses: дубликаты cian_id', COUNT(*) - COUNT(DISTINCT cian_id)
FROM addresses
UNION ALL
SELECT 'realty_inside: дубликаты cian_id', COUNT(*) - COUNT(DISTINCT cian_id)
FROM realty_inside
UNION ALL
SELECT 'realty_outside: дубликаты cian_id', COUNT(*) - COUNT(DISTINCT cian_id)
FROM realty_outside
UNION ALL
SELECT 'realty_details: дубликаты cian_id', COUNT(*) - COUNT(DISTINCT cian_id)
FROM realty_details
UNION ALL
SELECT 'offers_details: дубликаты cian_id', COUNT(*) - COUNT(DISTINCT cian_id)
FROM offers_details
UNION ALL
SELECT 'developers: дубликаты cian_id', COUNT(*) - COUNT(DISTINCT cian_id)
FROM developers;" 2>/dev/null
echo ""

# 5. Проверка данных в последних 5 объявлениях
echo "=== 5. ПРОВЕРКА ПОСЛЕДНИХ 5 ОБЪЯВЛЕНИЙ ==="
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT 
    o.cian_id,
    CASE WHEN a.cian_id IS NOT NULL THEN '✓' ELSE '✗' END as адрес,
    CASE WHEN ri.cian_id IS NOT NULL THEN '✓' ELSE '✗' END as внутри,
    CASE WHEN ro.cian_id IS NOT NULL THEN '✓' ELSE '✗' END as снаружи,
    CASE WHEN rd.cian_id IS NOT NULL THEN '✓' ELSE '✗' END as детали,
    CASE WHEN od.cian_id IS NOT NULL THEN '✓' ELSE '✗' END as объявление,
    CASE WHEN d.cian_id IS NOT NULL THEN '✓' ELSE '✗' END as застройщик,
    DATE_FORMAT(o.created_at, '%H:%i:%s') as время
FROM offers o
LEFT JOIN addresses a ON o.cian_id = a.cian_id
LEFT JOIN realty_inside ri ON o.cian_id = ri.cian_id
LEFT JOIN realty_outside ro ON o.cian_id = ro.cian_id
LEFT JOIN realty_details rd ON o.cian_id = rd.cian_id
LEFT JOIN offers_details od ON o.cian_id = od.cian_id
LEFT JOIN developers d ON o.cian_id = d.cian_id
ORDER BY o.created_at DESC
LIMIT 5;" 2>/dev/null
echo ""

# 6. Статистика заполненности полей
echo "=== 6. СТАТИСТИКА ЗАПОЛНЕННОСТИ ПОЛЕЙ ==="
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT 
    'addresses: district заполнено' as поле,
    COUNT(*) as всего,
    SUM(CASE WHEN district IS NOT NULL THEN 1 ELSE 0 END) as заполнено,
    ROUND(SUM(CASE WHEN district IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as процент
FROM addresses
UNION ALL
SELECT 'addresses: metro заполнено', COUNT(*), SUM(CASE WHEN metro IS NOT NULL THEN 1 ELSE 0 END), ROUND(SUM(CASE WHEN metro IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
FROM addresses
UNION ALL
SELECT 'realty_inside: rooms_count заполнено', COUNT(*), SUM(CASE WHEN rooms_count IS NOT NULL THEN 1 ELSE 0 END), ROUND(SUM(CASE WHEN rooms_count IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
FROM realty_inside
UNION ALL
SELECT 'realty_inside: total_area заполнено', COUNT(*), SUM(CASE WHEN total_area IS NOT NULL THEN 1 ELSE 0 END), ROUND(SUM(CASE WHEN total_area IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
FROM realty_inside
UNION ALL
SELECT 'realty_outside: build_year заполнено', COUNT(*), SUM(CASE WHEN build_year IS NOT NULL THEN 1 ELSE 0 END), ROUND(SUM(CASE WHEN build_year IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
FROM realty_outside
UNION ALL
SELECT 'offers_details: description заполнено', COUNT(*), SUM(CASE WHEN description IS NOT NULL AND description != '' THEN 1 ELSE 0 END), ROUND(SUM(CASE WHEN description IS NOT NULL AND description != '' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
FROM offers_details;" 2>/dev/null
echo ""

# 7. Проверка на "осиротевшие" записи (записи без основного объявления)
echo "=== 7. ПРОВЕРКА НА 'ОСИРОТЕВШИЕ' ЗАПИСИ ==="
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT 
    'addresses без offers' as проблема, COUNT(*) as количество
FROM addresses a
LEFT JOIN offers o ON a.cian_id = o.cian_id
WHERE o.cian_id IS NULL
UNION ALL
SELECT 'realty_inside без offers', COUNT(*)
FROM realty_inside ri
LEFT JOIN offers o ON ri.cian_id = o.cian_id
WHERE o.cian_id IS NULL
UNION ALL
SELECT 'realty_outside без offers', COUNT(*)
FROM realty_outside ro
LEFT JOIN offers o ON ro.cian_id = o.cian_id
WHERE o.cian_id IS NULL
UNION ALL
SELECT 'realty_details без offers', COUNT(*)
FROM realty_details rd
LEFT JOIN offers o ON rd.cian_id = o.cian_id
WHERE o.cian_id IS NULL
UNION ALL
SELECT 'offers_details без offers', COUNT(*)
FROM offers_details od
LEFT JOIN offers o ON od.cian_id = o.cian_id
WHERE o.cian_id IS NULL
UNION ALL
SELECT 'developers без offers', COUNT(*)
FROM developers d
LEFT JOIN offers o ON d.cian_id = o.cian_id
WHERE o.cian_id IS NULL;" 2>/dev/null
echo ""

# 8. Итоговый отчет
echo "=== 8. ИТОГОВЫЙ ОТЧЕТ ==="
TOTAL_OFFERS=$(docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "SELECT COUNT(*) FROM offers;" 2>/dev/null | tail -1 | tr -d ' ')
COMPLETE_OFFERS=$(docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT COUNT(*) FROM offers o
WHERE EXISTS (SELECT 1 FROM addresses a WHERE a.cian_id = o.cian_id)
AND EXISTS (SELECT 1 FROM realty_inside ri WHERE ri.cian_id = o.cian_id)
AND EXISTS (SELECT 1 FROM realty_outside ro WHERE ro.cian_id = o.cian_id)
AND EXISTS (SELECT 1 FROM realty_details rd WHERE rd.cian_id = o.cian_id)
AND EXISTS (SELECT 1 FROM offers_details od WHERE od.cian_id = o.cian_id)
AND EXISTS (SELECT 1 FROM developers d WHERE d.cian_id = o.cian_id);" 2>/dev/null | tail -1 | tr -d ' ')

if [ -n "$TOTAL_OFFERS" ] && [ "$TOTAL_OFFERS" -gt 0 ]; then
    PERCENT=$(echo "scale=1; $COMPLETE_OFFERS * 100 / $TOTAL_OFFERS" | bc)
    echo "Всего объявлений: $TOTAL_OFFERS"
    echo "Полностью заполненных (со всеми таблицами): $COMPLETE_OFFERS ($PERCENT%)"
    
    if [ "$COMPLETE_OFFERS" -eq "$TOTAL_OFFERS" ]; then
        echo "✓ ВСЕ ОБЪЯВЛЕНИЯ ПОЛНОСТЬЮ ЗАПОЛНЕНЫ!"
    else
        INCOMPLETE=$((TOTAL_OFFERS - COMPLETE_OFFERS))
        echo "⚠ Неполных объявлений: $INCOMPLETE"
    fi
fi
echo ""

echo "=== ПРОВЕРКА ЗАВЕРШЕНА ==="

