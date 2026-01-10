#!/bin/bash
# Просмотр данных из всех таблиц базы данных

cd /root/rentsense || exit 1

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          ПРОСМОТР ДАННЫХ ИЗ БАЗЫ ДАННЫХ                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Получаем последний cian_id
LATEST_CIAN_ID=$(docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT cian_id FROM offers ORDER BY created_at DESC LIMIT 1;" 2>/dev/null | tail -1 | tr -d ' ')

if [ -z "$LATEST_CIAN_ID" ] || [ "$LATEST_CIAN_ID" = "cian_id" ]; then
    echo "База данных пуста или нет данных"
    exit 1
fi

echo "Просматриваем данные для последнего объявления: cian_id = $LATEST_CIAN_ID"
echo ""

# 1. Таблица offers
echo "════════════════════════════════════════════════════════════"
echo "1. ТАБЛИЦА: offers (основная информация об объявлении)"
echo "════════════════════════════════════════════════════════════"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "
SELECT 
    id, 
    cian_id, 
    price, 
    category, 
    views_count, 
    photos_count, 
    floor_number, 
    floors_count, 
    publication_at,
    created_at,
    updated_at
FROM offers 
WHERE cian_id = $LATEST_CIAN_ID;" 2>/dev/null
echo ""

# 2. Таблица addresses
echo "════════════════════════════════════════════════════════════"
echo "2. ТАБЛИЦА: addresses (адрес и метро)"
echo "════════════════════════════════════════════════════════════"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "
SELECT 
    id,
    cian_id,
    county,
    district,
    street,
    house,
    metro,
    travel_type,
    travel_time,
    address,
    coordinates
FROM addresses 
WHERE cian_id = $LATEST_CIAN_ID;" 2>/dev/null
echo ""

# 3. Таблица realty_inside
echo "════════════════════════════════════════════════════════════"
echo "3. ТАБЛИЦА: realty_inside (внутренние характеристики)"
echo "════════════════════════════════════════════════════════════"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "
SELECT 
    id,
    cian_id,
    repair_type,
    total_area,
    living_area,
    kitchen_area,
    ceiling_height,
    balconies,
    loggias,
    rooms_count,
    separated_wc,
    combined_wc,
    windows_view
FROM realty_inside 
WHERE cian_id = $LATEST_CIAN_ID;" 2>/dev/null
echo ""

# 4. Таблица realty_outside
echo "════════════════════════════════════════════════════════════"
echo "4. ТАБЛИЦА: realty_outside (внешние характеристики)"
echo "════════════════════════════════════════════════════════════"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "
SELECT 
    id,
    cian_id,
    build_year,
    entrances,
    material_type,
    parking_type,
    garbage_chute,
    lifts_count,
    passenger_lifts,
    cargo_lifts
FROM realty_outside 
WHERE cian_id = $LATEST_CIAN_ID;" 2>/dev/null
echo ""

# 5. Таблица realty_details
echo "════════════════════════════════════════════════════════════"
echo "5. ТАБЛИЦА: realty_details (детали недвижимости)"
echo "════════════════════════════════════════════════════════════"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "
SELECT 
    id,
    cian_id,
    realty_type,
    project_type,
    heat_type,
    gas_type,
    is_apartment,
    is_penthouse,
    is_mortgage_allowed,
    is_premium,
    is_emergency,
    renovation_programm,
    finish_date
FROM realty_details 
WHERE cian_id = $LATEST_CIAN_ID;" 2>/dev/null
echo ""

# 6. Таблица offers_details
echo "════════════════════════════════════════════════════════════"
echo "6. ТАБЛИЦА: offers_details (детали объявления)"
echo "════════════════════════════════════════════════════════════"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "
SELECT 
    id,
    cian_id,
    agent_name,
    deal_type,
    flat_type,
    sale_type,
    is_duplicate,
    LEFT(description, 200) as description_preview,
    payment_period,
    lease_term_type,
    deposit,
    prepay_months,
    utilities_included,
    client_fee,
    agent_fee
FROM offers_details 
WHERE cian_id = $LATEST_CIAN_ID;" 2>/dev/null
echo ""

# 7. Таблица developers
echo "════════════════════════════════════════════════════════════"
echo "7. ТАБЛИЦА: developers (застройщик)"
echo "════════════════════════════════════════════════════════════"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "
SELECT 
    id,
    cian_id,
    name,
    review_count,
    total_rate,
    buildings_count,
    foundation_year,
    is_reliable
FROM developers 
WHERE cian_id = $LATEST_CIAN_ID;" 2>/dev/null
echo ""

# Статистика по всем таблицам
echo "════════════════════════════════════════════════════════════"
echo "СТАТИСТИКА ПО ВСЕМ ТАБЛИЦАМ:"
echo "════════════════════════════════════════════════════════════"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "
SELECT 
    'offers' as table_name, COUNT(*) as rows FROM offers
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
echo ""

echo "Для просмотра другого объявления, укажите cian_id:"
echo "  docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e \"SELECT * FROM offers WHERE cian_id = YOUR_CIAN_ID;\""

