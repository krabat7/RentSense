#!/bin/bash
cd /root/rentsense || exit 1

LOG_LINES=2000

echo "=== АНАЛИЗ ПАТТЕРНОВ БЛОКИРОВОК ПРОКСИ ==="
echo ""

# 1. Общая статистика
echo "1. ОБЩАЯ СТАТИСТИКА:"
SUCCESS=$(docker-compose -f docker-compose.prod.yml logs --tail=$LOG_LINES parser | grep -c "is adding" || echo "0")
ERRORS_403=$(docker-compose -f docker-compose.prod.yml logs --tail=$LOG_LINES parser | grep -c "403" || echo "0")
ERRORS_CAPTCHA=$(docker-compose -f docker-compose.prod.yml logs --tail=$LOG_LINES parser | grep -c "captcha" || echo "0")
ERRORS_BLOCKED=$(docker-compose -f docker-compose.prod.yml logs --tail=$LOG_LINES parser | grep -c "blocked" || echo "0")
TOTAL=$((SUCCESS + ERRORS_403 + ERRORS_CAPTCHA))

echo "Успешных: $SUCCESS"
echo "Ошибок 403: $ERRORS_403"
echo "Ошибок captcha: $ERRORS_CAPTCHA"
echo "Блокировок: $ERRORS_BLOCKED"
if [ "$TOTAL" -gt 0 ]; then
    RATE=$(echo "scale=1; ($ERRORS_403 + $ERRORS_CAPTCHA) * 100 / $TOTAL" | bc 2>/dev/null || echo "0")
    echo "Процент ошибок: ${RATE}%"
fi
echo ""

# 2. Анализ последовательностей
echo "2. ПОСЛЕДОВАТЕЛЬНОСТИ (успех -> ошибка):"
echo "Последние 10 блокировок с контекстом:"
docker-compose -f docker-compose.prod.yml logs --tail=$LOG_LINES parser | grep -B 3 "blocked\|403\|captcha" | grep -E "(is adding|403|blocked|captcha|Playwright time)" | tail -40
echo ""

# 3. Время между запросами
echo "3. ВРЕМЯ МЕЖДУ ЗАПРОСАМИ (последние 20):"
docker-compose -f docker-compose.prod.yml logs --tail=$LOG_LINES parser | grep "Playwright time" | tail -20
echo ""

# 4. Статистика по прокси
echo "4. СТАТИСТИКА ПО ПРОКСИ:"
echo "Успешные запросы:"
docker-compose -f docker-compose.prod.yml logs --tail=$LOG_LINES parser | grep "Playwright time" | awk '{print $NF}' | sort | uniq -c | sort -rn | head -10
echo ""
echo "Блокировки:"
docker-compose -f docker-compose.prod.yml logs --tail=$LOG_LINES parser | grep -E "(blocked|403)" | grep -oE "http://[^ ]+" | sort | uniq -c | sort -rn | head -10
echo ""

# 5. Рекомендации
echo "5. РЕКОМЕНДАЦИИ:"
if [ "$RATE" != "0" ] && [ -n "$RATE" ]; then
    if (( $(echo "$RATE > 50" | bc -l 2>/dev/null || echo "0") )); then
        echo "⚠ Слишком много ошибок (>50%) - увеличить задержку до 30-35 сек"
    elif (( $(echo "$RATE > 30" | bc -l 2>/dev/null || echo "0") )); then
        echo "⚠ Много ошибок (30-50%) - увеличить задержку до 25-30 сек"
    elif (( $(echo "$RATE > 20" | bc -l 2>/dev/null || echo "0") )); then
        echo "⚠ Умеренные ошибки (20-30%) - попробовать 22-25 сек"
    else
        echo "✓ Ошибок мало (<20%) - текущая задержка (20 сек) оптимальна"
    fi
fi
