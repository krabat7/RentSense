#!/bin/bash
# Просмотр данных из всех таблиц с правильной кодировкой

cd /root/rentsense || exit 1

# Получаем последний cian_id
LATEST_CIAN_ID=$(docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT cian_id FROM offers ORDER BY created_at DESC LIMIT 1;" 2>/dev/null | tail -1 | tr -d ' ')

if [ -z "$LATEST_CIAN_ID" ] || [ "$LATEST_CIAN_ID" = "cian_id" ]; then
    echo "База данных пуста"
    exit 1
fi

echo "Просматриваем данные для последнего объявления: cian_id = $LATEST_CIAN_ID"
echo ""

# Устанавливаем правильную кодировку для MySQL
MYSQL_CMD="mysql -uroot -pRentSense2025\!Secure rentsense --default-character-set=utf8mb4"

# 1. offers
echo "=== 1. ТАБЛИЦА: offers (основная информация) ==="
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT 
    id, 
    cian_id, 
    CONCAT(price, ' руб.') as price,
    category,
    photos_count as photos,
    CONCAT(floor_number, '/', floors_count) as floor,
    DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') as created_at
FROM offers 
WHERE cian_id = $LATEST_CIAN_ID;" 2>/dev/null
echo ""

# 2. addresses
echo "=== 2. ТАБЛИЦА: addresses (адрес) ==="
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT 
    id,
    cian_id,
    county as округ,
    district as район,
    street as улица,
    house as дом,
    metro as метро,
    CONCAT(travel_time, ' мин') as время_до_метро
FROM addresses 
WHERE cian_id = $LATEST_CIAN_ID;" 2>/dev/null
echo ""

# 3. realty_inside
echo "=== 3. ТАБЛИЦА: realty_inside (внутренние характеристики) ==="
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT 
    id,
    cian_id,
    repair_type as тип_ремонта,
    CONCAT(total_area, ' м²') as общая_площадь,
    CONCAT(COALESCE(living_area, 'NULL'), ' м²') as жилая_площадь,
    CONCAT(kitchen_area, ' м²') as площадь_кухни,
    rooms_count as комнат,
    balconies as балконов
FROM realty_inside 
WHERE cian_id = $LATEST_CIAN_ID;" 2>/dev/null
echo ""

# 4. realty_outside
echo "=== 4. ТАБЛИЦА: realty_outside (внешние характеристики) ==="
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT 
    id,
    cian_id,
    build_year as год_постройки,
    material_type as материал,
    parking_type as парковка,
    lifts_count as лифтов
FROM realty_outside 
WHERE cian_id = $LATEST_CIAN_ID;" 2>/dev/null
echo ""

# 5. realty_details
echo "=== 5. ТАБЛИЦА: realty_details (детали недвижимости) ==="
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT 
    id,
    cian_id,
    realty_type as тип_недвижимости,
    CASE WHEN is_apartment = 1 THEN 'Да' ELSE 'Нет' END as апартаменты,
    CASE WHEN is_penthouse = 1 THEN 'Да' ELSE 'Нет' END as пентхаус,
    CASE WHEN is_premium = 1 THEN 'Да' ELSE 'Нет' END as премиум
FROM realty_details 
WHERE cian_id = $LATEST_CIAN_ID;" 2>/dev/null
echo ""

# 6. offers_details
echo "=== 6. ТАБЛИЦА: offers_details (детали объявления) ==="
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT 
    id,
    cian_id,
    deal_type as тип_сделки,
    flat_type as тип_квартиры,
    CONCAT(LEFT(description, 150), '...') as описание,
    CONCAT(deposit, ' руб.') as залог,
    CASE WHEN utilities_included = 1 THEN 'Да' ELSE 'Нет' END as коммуналка_включена
FROM offers_details 
WHERE cian_id = $LATEST_CIAN_ID;" 2>/dev/null
echo ""

# 7. developers
echo "=== 7. ТАБЛИЦА: developers (застройщик) ==="
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT 
    id,
    cian_id,
    name as название,
    total_rate as рейтинг,
    buildings_count as количество_домов
FROM developers 
WHERE cian_id = $LATEST_CIAN_ID;" 2>/dev/null
echo ""

# Сводная информация
echo "=== СВОДНАЯ ИНФОРМАЦИЯ ==="
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT 
    o.cian_id,
    CONCAT(o.price, ' руб.') as цена,
    CONCAT(ri.rooms_count, ' комн., ', ri.total_area, ' м²') as параметры,
    CONCAT(a.district, ', ', a.metro) as локация,
    CONCAT(ro.build_year, ' г., ', ro.material_type) as дом,
    DATE_FORMAT(o.created_at, '%Y-%m-%d %H:%i:%s') as добавлено
FROM offers o
LEFT JOIN addresses a ON o.cian_id = a.cian_id
LEFT JOIN realty_inside ri ON o.cian_id = ri.cian_id
LEFT JOIN realty_outside ro ON o.cian_id = ro.cian_id
WHERE o.cian_id = $LATEST_CIAN_ID;" 2>/dev/null
echo ""

# Статистика
echo "=== СТАТИСТИКА ПО ТАБЛИЦАМ ==="
docker-compose -f docker-compose.prod.yml exec -T mysql $MYSQL_CMD -e "
SELECT 
    'offers' as таблица, COUNT(*) as строк FROM offers
UNION ALL
SELECT 'addresses', COUNT(*) FROM addresses
UNION ALL
SELECT 'realty_inside', COUNT(*) FROM realty_inside
UNION ALL
SELECT 'realty_outside', COUNT(*) FROM realty_outside
UNION ALL
SELECT 'realty_details', COUNT(*) FROM realty_details
UNION ALL
SELECT 'offers_details', COUNT(*) FROM offers_details
UNION ALL
SELECT 'developers', COUNT(*) FROM developers;" 2>/dev/null

