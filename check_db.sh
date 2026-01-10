#!/bin/bash
# Проверка данных в базе

cd /root/rentsense || exit 1

echo "=== Database Statistics ==="
echo ""
echo "Total offers:"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT COUNT(*) as total_offers FROM offers;"
echo ""
echo "Last 10 offers (cian_id, price, created_at):"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT cian_id, price, created_at FROM offers ORDER BY created_at DESC LIMIT 10;"
echo ""
echo "Statistics by date (last 5 days):"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT DATE(created_at) as date, COUNT(*) as count FROM offers GROUP BY DATE(created_at) ORDER BY date DESC LIMIT 5;"
echo ""
echo "Offers added in last hour:"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT COUNT(*) as count FROM offers WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR);"
echo ""
echo "Offers added in last 24 hours:"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT COUNT(*) as count FROM offers WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR);"

