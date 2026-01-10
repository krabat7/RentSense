#!/bin/bash
# Мониторинг скорости парсинга после оптимизаций

cd /root/rentsense || exit 1

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     МОНИТОРИНГ СКОРОСТИ ПАРСИНГА (после оптимизаций)     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Текущее время
echo "Время проверки: $(date)"
echo ""

# Проверка изменений в коде
echo "=== Проверка примененных оптимизаций ==="
echo "1. Задержка после успешного запроса (должна быть 20 секунд):"
grep -n "time.time() + 20" app/parser/main.py | head -2
echo ""

echo "2. Задержки внутри запроса (должны быть 2 секунды):"
grep -n "time.sleep(2)" app/parser/main.py | head -2
echo ""

echo "3. Интервал между циклами (должен быть 1800 секунд = 30 минут):"
grep -n "PARSE_INTERVAL = 1800" app/scheduler/crontab.py
echo ""

# Статистика из базы
echo "=== Статистика из базы данных ==="
echo "Всего объявлений:"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT COUNT(*) as total FROM offers;" 2>/dev/null | tail -1
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

# Статистика из логов
echo "=== Статистика из логов парсера (последние 200 строк) ==="
echo "Успешно добавлено объявлений:"
docker-compose -f docker-compose.prod.yml logs --tail=200 parser | grep -c "is adding" || echo "0"
echo ""

echo "Ошибок прокси (403/captcha/blocked):"
docker-compose -f docker-compose.prod.yml logs --tail=200 parser | grep -cE "(403|blocked|captcha)" || echo "0"
echo ""

echo "Время ожидания прокси (последние 5):"
docker-compose -f docker-compose.prod.yml logs --tail=200 parser | grep "No available proxies, waiting" | tail -5
echo ""

echo "Последние 5 добавленных объявлений:"
docker-compose -f docker-compose.prod.yml logs --tail=200 parser | grep "is adding" | tail -5
echo ""

echo "=== Оценка скорости ==="
RECENT_COUNT=$(docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT COUNT(*) as count FROM offers WHERE created_at >= DATE_SUB(NOW(), INTERVAL 10 MINUTE);" 2>/dev/null | tail -1 | tr -d ' ')
if [ -n "$RECENT_COUNT" ] && [ "$RECENT_COUNT" -gt 0 ]; then
    SPEED_PER_MIN=$(echo "scale=2; $RECENT_COUNT / 10" | bc)
    echo "Текущая скорость: ~$SPEED_PER_MIN объявлений/минуту"
    echo ""
    if (( $(echo "$SPEED_PER_MIN > 0.3" | bc -l) )); then
        echo "✓ Скорость хорошая! (цель: >0.3 объявлений/минуту)"
    else
        echo "⚠ Скорость ниже ожидаемой. Проверьте логи на ошибки."
    fi
else
    echo "⚠ Недостаточно данных за последние 10 минут"
fi
echo ""

echo "=== Рекомендации ==="
ERROR_COUNT=$(docker-compose -f docker-compose.prod.yml logs --tail=200 parser | grep -cE "(403|blocked|captcha)" || echo "0")
SUCCESS_COUNT=$(docker-compose -f docker-compose.prod.yml logs --tail=200 parser | grep -c "is adding" || echo "0")
if [ "$ERROR_COUNT" -gt 0 ] && [ "$SUCCESS_COUNT" -gt 0 ]; then
    ERROR_RATIO=$(echo "scale=1; $ERROR_COUNT * 100 / ($ERROR_COUNT + $SUCCESS_COUNT)" | bc)
    echo "Процент ошибок: ~${ERROR_RATIO}%"
    if (( $(echo "$ERROR_RATIO > 50" | bc -l) )); then
        echo "⚠ Слишком много ошибок! Рекомендуется увеличить задержки."
    else
        echo "✓ Уровень ошибок приемлемый"
    fi
fi
echo ""

