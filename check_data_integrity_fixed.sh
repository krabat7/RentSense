#!/bin/bash
cd /root/rentsense || exit 1

echo "=== ПРОВЕРКА ЦЕЛОСТНОСТИ ДАННЫХ ==="
echo ""

# 1. Количество записей
echo "1. КОЛИЧЕСТВО ЗАПИСЕЙ:"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT 'offers' as table_name, COUNT(*) as rows FROM offers UNION ALL SELECT 'addresses', COUNT(*) FROM addresses UNION ALL SELECT 'realty_inside', COUNT(*) FROM realty_inside UNION ALL SELECT 'realty_outside', COUNT(*) FROM realty_outside UNION ALL SELECT 'realty_details', COUNT(*) FROM realty_details UNION ALL SELECT 'offers_details', COUNT(*) FROM offers_details UNION ALL SELECT 'developers', COUNT(*) FROM developers;" 2>/dev/null
echo ""

# 2. Проверка связей
echo "2. ПРОВЕРКА СВЯЗЕЙ (должно быть 0):"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT 'Without address' as issue, COUNT(*) as count FROM offers o LEFT JOIN addresses a ON o.cian_id = a.cian_id WHERE a.cian_id IS NULL UNION ALL SELECT 'Without realty_inside', COUNT(*) FROM offers o LEFT JOIN realty_inside ri ON o.cian_id = ri.cian_id WHERE ri.cian_id IS NULL UNION ALL SELECT 'Without realty_outside', COUNT(*) FROM offers o LEFT JOIN realty_outside ro ON o.cian_id = ro.cian_id WHERE ro.cian_id IS NULL UNION ALL SELECT 'Without realty_details', COUNT(*) FROM offers o LEFT JOIN realty_details rd ON o.cian_id = rd.cian_id WHERE rd.cian_id IS NULL UNION ALL SELECT 'Without offers_details', COUNT(*) FROM offers o LEFT JOIN offers_details od ON o.cian_id = od.cian_id WHERE od.cian_id IS NULL UNION ALL SELECT 'Without developers', COUNT(*) FROM offers o LEFT JOIN developers d ON o.cian_id = d.cian_id WHERE d.cian_id IS NULL;" 2>/dev/null
echo ""

# 3. Проверка критичных полей
echo "3. ПРОВЕРКА КРИТИЧНЫХ ПОЛЕЙ (должно быть 0):"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT 'offers: price NULL' as issue, COUNT(*) as count FROM offers WHERE price IS NULL UNION ALL SELECT 'offers: cian_id NULL', COUNT(*) FROM offers WHERE cian_id IS NULL;" 2>/dev/null
echo ""

# 4. Проверка дубликатов
echo "4. ПРОВЕРКА ДУБЛИКАТОВ (должно быть 0):"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT 'offers: duplicates' as issue, COUNT(*) - COUNT(DISTINCT cian_id) as count FROM offers UNION ALL SELECT 'addresses: duplicates', COUNT(*) - COUNT(DISTINCT cian_id) FROM addresses;" 2>/dev/null
echo ""

# 5. Последние 5 объявлений
echo "5. ПОСЛЕДНИЕ 5 ОБЪЯВЛЕНИЙ:"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT o.cian_id, CASE WHEN a.cian_id IS NOT NULL THEN 'YES' ELSE 'NO' END as address, CASE WHEN ri.cian_id IS NOT NULL THEN 'YES' ELSE 'NO' END as inside, CASE WHEN ro.cian_id IS NOT NULL THEN 'YES' ELSE 'NO' END as outside, CASE WHEN rd.cian_id IS NOT NULL THEN 'YES' ELSE 'NO' END as details, CASE WHEN od.cian_id IS NOT NULL THEN 'YES' ELSE 'NO' END as offer_details, CASE WHEN d.cian_id IS NOT NULL THEN 'YES' ELSE 'NO' END as developer FROM offers o LEFT JOIN addresses a ON o.cian_id = a.cian_id LEFT JOIN realty_inside ri ON o.cian_id = ri.cian_id LEFT JOIN realty_outside ro ON o.cian_id = ro.cian_id LEFT JOIN realty_details rd ON o.cian_id = rd.cian_id LEFT JOIN offers_details od ON o.cian_id = od.cian_id LEFT JOIN developers d ON o.cian_id = d.cian_id ORDER BY o.created_at DESC LIMIT 5;" 2>/dev/null
echo ""

# 6. Итоговый отчет
echo "6. ИТОГОВЫЙ ОТЧЕТ:"
TOTAL=$(docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT COUNT(*) FROM offers;" 2>/dev/null | tail -1 | tr -d ' ')
COMPLETE=$(docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT COUNT(*) FROM offers o WHERE EXISTS (SELECT 1 FROM addresses a WHERE a.cian_id = o.cian_id) AND EXISTS (SELECT 1 FROM realty_inside ri WHERE ri.cian_id = o.cian_id) AND EXISTS (SELECT 1 FROM realty_outside ro WHERE ro.cian_id = o.cian_id) AND EXISTS (SELECT 1 FROM realty_details rd WHERE rd.cian_id = o.cian_id) AND EXISTS (SELECT 1 FROM offers_details od WHERE od.cian_id = o.cian_id) AND EXISTS (SELECT 1 FROM developers d WHERE d.cian_id = o.cian_id);" 2>/dev/null | tail -1 | tr -d ' ')

if [ -n "$TOTAL" ] && [ "$TOTAL" -gt 0 ]; then
    PERCENT=$(echo "scale=1; $COMPLETE * 100 / $TOTAL" | bc 2>/dev/null || echo "0")
    echo "Total offers: $TOTAL"
    echo "Complete offers (all tables): $COMPLETE ($PERCENT%)"
    if [ "$COMPLETE" -eq "$TOTAL" ]; then
        echo "✓ ALL OFFERS ARE COMPLETE!"
    else
        INCOMPLETE=$((TOTAL - COMPLETE))
        echo "⚠ Incomplete offers: $INCOMPLETE"
    fi
fi
