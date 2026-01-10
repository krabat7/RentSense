#!/bin/bash
cd /root/rentsense || exit 1
echo "=== Мониторинг скорости парсинга ==="
echo "Время: $(date)"
echo ""
echo "Добавлено за последний час:"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT COUNT(*) as count FROM offers WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR);" 2>/dev/null | tail -1
echo ""
echo "Добавлено за последние 30 минут:"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT COUNT(*) as count FROM offers WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 MINUTE);" 2>/dev/null | tail -1
echo ""
echo "Добавлено за последние 10 минут:"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT COUNT(*) as count FROM offers WHERE created_at >= DATE_SUB(NOW(), INTERVAL 10 MINUTE);" 2>/dev/null | tail -1
echo ""
echo "Успешно добавлено (из логов, последние 200 строк):"
docker-compose -f docker-compose.prod.yml logs --tail=200 parser | grep -c "is adding" || echo "0"
echo ""
echo "Ошибок прокси (последние 200 строк):"
docker-compose -f docker-compose.prod.yml logs --tail=200 parser | grep -cE "(403|blocked|captcha)" || echo "0"
echo ""
echo "Последние 5 добавленных объявлений:"
docker-compose -f docker-compose.prod.yml logs --tail=200 parser | grep "is adding" | tail -5
