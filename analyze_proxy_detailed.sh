#!/bin/bash
# Детальный анализ паттернов блокировок прокси

cd /root/rentsense || exit 1

LOG_LINES=3000

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     ДЕТАЛЬНЫЙ АНАЛИЗ ПАТТЕРНОВ БЛОКИРОВОК ПРОКСИ         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 1. Общая статистика
echo "=== 1. ОБЩАЯ СТАТИСТИКА (последние $LOG_LINES строк) ==="
SUCCESS=$(docker-compose -f docker-compose.prod.yml logs --tail=$LOG_LINES parser | grep -c "is adding" || echo "0")
ERRORS_403=$(docker-compose -f docker-compose.prod.yml logs --tail=$LOG_LINES parser | grep -c "403" || echo "0")
ERRORS_CAPTCHA=$(docker-compose -f docker-compose.prod.yml logs --tail=$LOG_LINES parser | grep -c "captcha" || echo "0")
ERRORS_BLOCKED=$(docker-compose -f docker-compose.prod.yml logs --tail=$LOG_LINES parser | grep -c "blocked" || echo "0")
TOTAL_REQUESTS=$((SUCCESS + ERRORS_403 + ERRORS_CAPTCHA))

echo "Успешных добавлений: $SUCCESS"
echo "Ошибок 403: $ERRORS_403"
echo "Ошибок captcha: $ERRORS_CAPTCHA"
echo "Блокировок прокси: $ERRORS_BLOCKED"
if [ "$TOTAL_REQUESTS" -gt 0 ]; then
    ERROR_RATE=$(echo "scale=1; ($ERRORS_403 + $ERRORS_CAPTCHA) * 100 / $TOTAL_REQUESTS" | bc 2>/dev/null || echo "0")
    echo "Процент ошибок: ${ERROR_RATE}%"
fi
echo ""

# 2. Анализ времени между запросами
echo "=== 2. АНАЛИЗ ВРЕМЕНИ МЕЖДУ ЗАПРОСАМИ ==="
echo "Последние 30 успешных запросов с временем:"
docker-compose -f docker-compose.prod.yml logs --tail=$LOG_LINES parser | grep "Playwright time" | tail -30 | awk '{print $1, $2, $NF}' | while read date time proxy; do
    echo "$date $time - $proxy"
done
echo ""

# 3. Паттерны: успех -> ошибка
echo "=== 3. ПАТТЕРНЫ: УСПЕХ -> ОШИБКА ==="
echo "Ищем случаи, когда после успешного запроса сразу идет ошибка:"
docker-compose -f docker-compose.prod.yml logs --tail=$LOG_LINES parser | grep -A 2 "is adding" | grep -E "(403|captcha|blocked)" | head -20
echo ""

# 4. Статистика по каждому прокси
echo "=== 4. СТАТИСТИКА ПО ПРОКСИ ==="
echo "Топ-10 прокси по количеству успешных запросов:"
docker-compose -f docker-compose.prod.yml logs --tail=$LOG_LINES parser | grep "Playwright time" | awk '{print $NF}' | sort | uniq -c | sort -rn | head -10
echo ""

echo "Топ-10 прокси по количеству ошибок:"
docker-compose -f docker-compose.prod.yml logs --tail=$LOG_LINES parser | grep -E "(403|captcha)" | grep -oE "http://[^ ]+" | sort | uniq -c | sort -rn | head -10
echo ""

# 5. Временные интервалы между запросами
echo "=== 5. ВРЕМЕННЫЕ ИНТЕРВАЛЫ МЕЖДУ ЗАПРОСАМИ ==="
echo "Анализ времени между запросами (последние 20):"
docker-compose -f docker-compose.prod.yml logs --tail=$LOG_LINES parser | grep "Playwright time" | tail -20 | awk '{print $1, $2}' | while read date time; do
    echo "$date $time"
done | python3 << 'PYEOF'
import sys
from datetime import datetime

times = []
for line in sys.stdin:
    try:
        # Парсим время из лога
        parts = line.strip().split()
        if len(parts) >= 2:
            time_str = f"{parts[0]} {parts[1]}"
            dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            times.append(dt)
    except:
        pass

if len(times) >= 2:
    intervals = []
    for i in range(1, len(times)):
        diff = (times[i] - times[i-1]).total_seconds()
        intervals.append(diff)
    
    if intervals:
        avg = sum(intervals) / len(intervals)
        min_int = min(intervals)
        max_int = max(intervals)
        print(f"Средний интервал: {avg:.1f} секунд")
        print(f"Минимальный: {min_int:.1f} секунд")
        print(f"Максимальный: {max_int:.1f} секунд")
PYEOF
echo ""

# 6. Рекомендации на основе анализа
echo "=== 6. РЕКОМЕНДАЦИИ ==="
if [ "$ERROR_RATE" != "0" ] && [ -n "$ERROR_RATE" ]; then
    if (( $(echo "$ERROR_RATE > 50" | bc -l 2>/dev/null || echo "0") )); then
        echo "⚠ КРИТИЧНО: Слишком много ошибок (>50%)!"
        echo "Рекомендация: Увеличить задержку до 30-35 секунд"
        echo "Текущая задержка: 20 секунд -> Нужно: 30-35 секунд"
    elif (( $(echo "$ERROR_RATE > 30" | bc -l 2>/dev/null || echo "0") )); then
        echo "⚠ Много ошибок (30-50%)"
        echo "Рекомендация: Увеличить задержку до 25-30 секунд"
        echo "Текущая задержка: 20 секунд -> Нужно: 25-30 секунд"
    elif (( $(echo "$ERROR_RATE > 20" | bc -l 2>/dev/null || echo "0") )); then
        echo "⚠ Умеренное количество ошибок (20-30%)"
        echo "Рекомендация: Попробовать задержку 22-25 секунд"
    else
        echo "✓ Уровень ошибок приемлемый (<20%)"
        echo "Рекомендация: Текущая задержка оптимальна"
    fi
fi
echo ""

echo "=== АНАЛИЗ ЗАВЕРШЕН ==="

