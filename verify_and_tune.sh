#!/bin/bash
# Проверка оптимизаций и настройка баланса скорости/ошибок

cd /root/rentsense || exit 1

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     ПРОВЕРКА ОПТИМИЗАЦИЙ И АНАЛИЗ ПРОИЗВОДИТЕЛЬНОСТИ     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 1. Проверка примененных оптимизаций
echo "=== Проверка примененных оптимизаций ==="
echo "1. Задержка после успешного запроса:"
if grep -q "time.time() + 20" app/parser/main.py; then
    echo "   ✓ Применена: 20 секунд"
    DELAY_APPLIED=20
else
    echo "   ✗ Не найдена! Проверьте файл."
    DELAY_APPLIED=0
fi

echo ""
echo "2. Задержки внутри запроса:"
if grep -q "time.sleep(2)" app/parser/main.py; then
    echo "   ✓ Применены: 2 секунды"
else
    echo "   ✗ Не найдены!"
fi

echo ""
echo "3. Интервал между циклами:"
if grep -q "PARSE_INTERVAL = 1800" app/scheduler/crontab.py; then
    echo "   ✓ Применен: 1800 секунд (30 минут)"
else
    echo "   ✗ Не найден!"
fi

echo ""
echo "=== Анализ производительности ==="

# Статистика за последние 10 минут
RECENT_10=$(docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -pRentSense2025\!Secure rentsense -e "SELECT COUNT(*) as count FROM offers WHERE created_at >= DATE_SUB(NOW(), INTERVAL 10 MINUTE);" 2>/dev/null | tail -1 | tr -d ' ')

# Статистика из логов
SUCCESS_COUNT=$(docker-compose -f docker-compose.prod.yml logs --tail=200 parser | grep -c "is adding" || echo "0")
ERROR_COUNT=$(docker-compose -f docker-compose.prod.yml logs --tail=200 parser | grep -cE "(403|blocked|captcha)" || echo "0")

echo "Добавлено за последние 10 минут: $RECENT_10"
echo "Успешных добавлений (из логов): $SUCCESS_COUNT"
echo "Ошибок прокси (из логов): $ERROR_COUNT"

if [ "$ERROR_COUNT" -gt 0 ] && [ "$SUCCESS_COUNT" -gt 0 ]; then
    TOTAL=$((SUCCESS_COUNT + ERROR_COUNT))
    ERROR_PERCENT=$((ERROR_COUNT * 100 / TOTAL))
    echo "Процент ошибок: ${ERROR_PERCENT}%"
    
    if [ "$ERROR_PERCENT" -gt 50 ]; then
        echo ""
        echo "⚠ ВНИМАНИЕ: Слишком много ошибок (>50%)!"
        echo "Рекомендация: Увеличить задержку до 25-30 секунд"
        echo ""
        echo "Хотите увеличить задержку до 25 секунд? (y/n)"
        read -t 5 -n 1 answer || answer="n"
        if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
            echo ""
            echo "Увеличиваем задержку до 25 секунд..."
            sed -i 's/time\.time() + 20/time.time() + 25/g' app/parser/main.py
            docker-compose -f docker-compose.prod.yml restart parser
            echo "✓ Задержка увеличена до 25 секунд, парсер перезапущен"
        fi
    elif [ "$ERROR_PERCENT" -gt 30 ]; then
        echo ""
        echo "⚠ Много ошибок (30-50%). Рекомендуется мониторинг."
    else
        echo ""
        echo "✓ Уровень ошибок приемлемый (<30%)"
    fi
fi

echo ""
echo "=== Оценка скорости ==="
if [ -n "$RECENT_10" ] && [ "$RECENT_10" -gt 0 ]; then
    SPEED_PER_MIN=$(echo "scale=2; $RECENT_10 / 10" | bc 2>/dev/null || echo "0")
    SPEED_PER_HOUR=$(echo "scale=0; $SPEED_PER_MIN * 60" | bc 2>/dev/null || echo "0")
    echo "Текущая скорость: ~${SPEED_PER_MIN} объявлений/минуту"
    echo "Проекция на час: ~${SPEED_PER_HOUR} объявлений/час"
    
    if (( $(echo "$SPEED_PER_MIN > 0.3" | bc -l 2>/dev/null || echo "0") )); then
        echo "✓ Скорость хорошая! (цель: >0.3 объявлений/минуту)"
    else
        echo "⚠ Скорость ниже ожидаемой"
    fi
fi

echo ""
echo "=== Рекомендации ==="
if [ "$ERROR_PERCENT" -gt 50 ] && [ "$DELAY_APPLIED" -eq 20 ]; then
    echo "1. Увеличить задержку до 25-30 секунд для снижения ошибок"
    echo "2. Мониторить скорость - она может немного снизиться, но ошибок станет меньше"
elif [ "$ERROR_PERCENT" -lt 30 ] && [ "$DELAY_APPLIED" -eq 20 ]; then
    echo "1. Текущие настройки оптимальны!"
    echo "2. Продолжайте мониторинг"
fi

echo ""
echo "Для применения изменений задержки выполните:"
echo "  sed -i 's/time\\.time() + 20/time.time() + 25/g' app/parser/main.py"
echo "  docker-compose -f docker-compose.prod.yml restart parser"

