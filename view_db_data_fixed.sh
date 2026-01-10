#!/bin/bash
cd /root/rentsense || exit 1

LATEST_CIAN_ID=$(docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT cian_id FROM offers ORDER BY created_at DESC LIMIT 1;" 2>/dev/null | tail -1 | tr -d ' ')

if [ -z "$LATEST_CIAN_ID" ] || [ "$LATEST_CIAN_ID" = "cian_id" ]; then
    echo "База данных пуста"
    exit 1
fi

echo "Просматриваем данные для: cian_id = $LATEST_CIAN_ID"
echo ""

# Сводная информация (все данные в одном запросе)
echo "=== СВОДНАЯ ИНФОРМАЦИЯ ОБ ОБЪЯВЛЕНИИ ==="
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense --default-character-set=utf8mb4 -e "
SELECT 
    o.cian_id as 'ID',
    CONCAT(o.price, ' руб.') as 'Цена',
    CONCAT(ri.rooms_count, ' комн., ', ri.total_area, ' м²') as 'Параметры',
    CONCAT(a.district, ', ', a.metro) as 'Локация',
    CONCAT(ro.build_year, ' г., ', ro.material_type) as 'Дом',
    ri.repair_type as 'Ремонт',
    CONCAT(o.floor_number, '/', o.floors_count) as 'Этаж',
    o.photos_count as 'Фото',
    DATE_FORMAT(o.created_at, '%Y-%m-%d %H:%i:%s') as 'Добавлено'
FROM offers o
LEFT JOIN addresses a ON o.cian_id = a.cian_id
LEFT JOIN realty_inside ri ON o.cian_id = ri.cian_id
LEFT JOIN realty_outside ro ON o.cian_id = ro.cian_id
WHERE o.cian_id = $LATEST_CIAN_ID;" 2>/dev/null
echo ""

# Детальное описание
echo "=== ОПИСАНИЕ ==="
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense --default-character-set=utf8mb4 -e "
SELECT LEFT(description, 300) as 'Описание' FROM offers_details WHERE cian_id = $LATEST_CIAN_ID;" 2>/dev/null
echo ""

# Статистика
echo "=== СТАТИСТИКА ПО ТАБЛИЦАМ ==="
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense --default-character-set=utf8mb4 -e "
SELECT 
    'offers' as 'Таблица', COUNT(*) as 'Строк' FROM offers
UNION ALL SELECT 'addresses', COUNT(*) FROM addresses
UNION ALL SELECT 'realty_inside', COUNT(*) FROM realty_inside
UNION ALL SELECT 'realty_outside', COUNT(*) FROM realty_outside
UNION ALL SELECT 'realty_details', COUNT(*) FROM realty_details
UNION ALL SELECT 'offers_details', COUNT(*) FROM offers_details
UNION ALL SELECT 'developers', COUNT(*) FROM developers;" 2>/dev/null
