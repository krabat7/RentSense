#!/bin/bash
cd /root/rentsense || exit 1

# Получаем последний cian_id
LATEST_CIAN_ID=$(docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT cian_id FROM offers ORDER BY created_at DESC LIMIT 1;" 2>/dev/null | tail -1 | tr -d ' ')

if [ -z "$LATEST_CIAN_ID" ] || [ "$LATEST_CIAN_ID" = "cian_id" ]; then
    echo "База данных пуста"
    exit 1
fi

echo "Просматриваем данные для последнего объявления: cian_id = $LATEST_CIAN_ID"
echo ""

# 1. offers
echo "=== 1. ТАБЛИЦА: offers ==="
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT id, cian_id, price, category, photos_count, floor_number, floors_count, created_at FROM offers WHERE cian_id = $LATEST_CIAN_ID;" 2>/dev/null
echo ""

# 2. addresses
echo "=== 2. ТАБЛИЦА: addresses ==="
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT id, cian_id, county, district, street, house, metro, travel_time FROM addresses WHERE cian_id = $LATEST_CIAN_ID;" 2>/dev/null
echo ""

# 3. realty_inside
echo "=== 3. ТАБЛИЦА: realty_inside ==="
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT id, cian_id, repair_type, total_area, living_area, kitchen_area, rooms_count, balconies FROM realty_inside WHERE cian_id = $LATEST_CIAN_ID;" 2>/dev/null
echo ""

# 4. realty_outside
echo "=== 4. ТАБЛИЦА: realty_outside ==="
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT id, cian_id, build_year, material_type, parking_type, lifts_count FROM realty_outside WHERE cian_id = $LATEST_CIAN_ID;" 2>/dev/null
echo ""

# 5. realty_details
echo "=== 5. ТАБЛИЦА: realty_details ==="
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT id, cian_id, realty_type, is_apartment, is_penthouse, is_premium FROM realty_details WHERE cian_id = $LATEST_CIAN_ID;" 2>/dev/null
echo ""

# 6. offers_details
echo "=== 6. ТАБЛИЦА: offers_details ==="
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT id, cian_id, deal_type, flat_type, LEFT(description, 100) as desc_preview, deposit, utilities_included FROM offers_details WHERE cian_id = $LATEST_CIAN_ID;" 2>/dev/null
echo ""

# 7. developers
echo "=== 7. ТАБЛИЦА: developers ==="
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT id, cian_id, name, total_rate, buildings_count FROM developers WHERE cian_id = $LATEST_CIAN_ID;" 2>/dev/null
echo ""

# Статистика
echo "=== СТАТИСТИКА ПО ТАБЛИЦАМ ==="
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT 'offers' as table_name, COUNT(*) as rows FROM offers UNION ALL SELECT 'addresses', COUNT(*) FROM addresses UNION ALL SELECT 'realty_inside', COUNT(*) FROM realty_inside UNION ALL SELECT 'realty_outside', COUNT(*) FROM realty_outside UNION ALL SELECT 'realty_details', COUNT(*) FROM realty_details UNION ALL SELECT 'offers_details', COUNT(*) FROM offers_details UNION ALL SELECT 'developers', COUNT(*) FROM developers;" 2>/dev/null
