#!/bin/bash
# Анализ состояния прокси и производительности парсера

echo "╔════════════════════════════════════════════════════════════╗"
echo "║    АНАЛИЗ СОСТОЯНИЯ ПРОКСИ И ПРОИЗВОДИТЕЛЬНОСТИ           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

cd /root/rentsense || exit 1

# Временной диапазон анализа (последние 2 часа)
HOURS=2

echo "📊 СТАТИСТИКА ДОБАВЛЕННЫХ ОБЪЯВЛЕНИЙ (последние ${HOURS} часа):"
echo "─────────────────────────────────────────────────────────────"
added_count=$(docker-compose -f docker-compose.prod.yml logs --since ${HOURS}h parser 2>/dev/null | grep -c "is adding" 2>/dev/null || echo "0")
echo "  ✓ Добавлено объявлений: $added_count"
echo ""

# Анализ ошибок прокси
echo "⚠️  АНАЛИЗ ОШИБОК ПРОКСИ (последние ${HOURS} часа):"
echo "─────────────────────────────────────────────────────────────"

# Статистика по типам ошибок (ограничиваем объем логов для производительности)
timeout_count=$(docker-compose -f docker-compose.prod.yml logs --tail 5000 --since ${HOURS}h parser 2>/dev/null | grep -c "Timeout.*exceeded" 2>/dev/null)
status_403=$(docker-compose -f docker-compose.prod.yml logs --tail 5000 --since ${HOURS}h parser 2>/dev/null | grep -c "Status=403" 2>/dev/null)
status_407=$(docker-compose -f docker-compose.prod.yml logs --tail 5000 --since ${HOURS}h parser 2>/dev/null | grep -c "Status=407" 2>/dev/null)
status_200=$(docker-compose -f docker-compose.prod.yml logs --tail 5000 --since ${HOURS}h parser 2>/dev/null | grep -c "Status=200" 2>/dev/null)
recjson_errors=$(docker-compose -f docker-compose.prod.yml logs --tail 5000 --since ${HOURS}h parser 2>/dev/null | grep -c "Recjson not match" 2>/dev/null)
blocked_proxies=$(docker-compose -f docker-compose.prod.yml logs --tail 5000 --since ${HOURS}h parser 2>/dev/null | grep -c "blocked for" 2>/dev/null)

# Убеждаемся, что переменные - числа
timeout_count=${timeout_count:-0}
status_403=${status_403:-0}
status_407=${status_407:-0}
status_200=${status_200:-0}
recjson_errors=${recjson_errors:-0}
blocked_proxies=${blocked_proxies:-0}

echo "  ✅ Успешных запросов (200): $status_200"
echo "  ⏱️  Таймаутов: $timeout_count"
echo "  🚫 Блокировок 403: $status_403"
echo "  🔐 Блокировок 407: $status_407"
echo "  ❌ Ошибок парсинга (Recjson): $recjson_errors"
echo "  🚫 Прокси заблокировано: $blocked_proxies"
echo ""

# Расчет процента успешности
total_requests=$((status_200 + status_403 + status_407 + timeout_count))
if [ "$total_requests" -gt 0 ] 2>/dev/null; then
    success_rate=$(awk "BEGIN {printf \"%.1f\", ($status_200 * 100) / $total_requests}" 2>/dev/null || echo "0")
    echo "  📈 Процент успешных запросов: ${success_rate}%"
else
    echo "  📈 Процент успешных запросов: нет данных"
fi
echo ""

# Анализ скорости парсинга
echo "⏱️  АНАЛИЗ СКОРОСТИ ПАРСИНГА:"
echo "─────────────────────────────────────────────────────────────"

# Время последнего добавления
last_added=$(docker-compose -f docker-compose.prod.yml logs parser 2>/dev/null | grep "is adding" | tail -1 | awk -F'|' '{print $1}' | xargs)
if [ -n "$last_added" ]; then
    echo "  🕐 Последнее добавление: $last_added"
    
    # Время последнего успешного запроса
    last_200=$(docker-compose -f docker-compose.prod.yml logs parser 2>/dev/null | grep "Status=200" | tail -1 | awk -F'|' '{print $1}' | xargs)
    if [ -n "$last_200" ]; then
        echo "  🕐 Последний успешный запрос: $last_200"
    fi
fi

# Среднее время запросов (успешных) - ограничиваем объем для производительности
echo ""
echo "  ⏱️  Среднее время запросов (последние 20 успешных):"
times=$(docker-compose -f docker-compose.prod.yml logs --tail 2000 --since ${HOURS}h parser 2>/dev/null | grep "Status=200" | sed -n 's/.*time=\([0-9.]*\)s.*/\1/p' | tail -20)
if [ -n "$times" ] && [ "$(echo "$times" | wc -l)" -gt 0 ]; then
    avg_time=$(echo "$times" | awk '{sum+=$1; count++} END {if(count>0) printf "%.2f", sum/count; else print "0"}')
    min_time=$(echo "$times" | awk 'BEGIN{min=999} {if($1<min && $1>0) min=$1} END {if(min==999) print "0"; else printf "%.2f", min}')
    max_time=$(echo "$times" | awk 'BEGIN{max=0} {if($1>max) max=$1} END {if(max==0) print "0"; else printf "%.2f", max}')
    echo "    Среднее: ${avg_time}s"
    echo "    Минимум: ${min_time}s"
    echo "    Максимум: ${max_time}s"
else
    echo "    Нет данных"
fi
echo ""

# Анализ активности прокси
echo "🌐 АНАЛИЗ АКТИВНОСТИ ПРОКСИ (последние 30 минут):"
echo "─────────────────────────────────────────────────────────────"

# Уникальные прокси за последние 30 минут (без -P для совместимости)
active_proxies=$(docker-compose -f docker-compose.prod.yml logs --tail 2000 --since 30m parser 2>/dev/null | grep "getResponse: URL=" | sed -n 's/.*proxy=\([^\.]*\)\.\.\..*/\1/p' | sort -u | wc -l)
active_proxies=${active_proxies:-0}
echo "  🔢 Активных прокси за последние 30 мин: $active_proxies"

# Последние 10 использованных прокси
echo ""
echo "  📋 Последние 10 использованных прокси:"
docker-compose -f docker-compose.prod.yml logs --tail 100 parser 2>/dev/null | grep "getResponse: URL=" | sed -n 's/.*proxy=\([^\.]*\)\.\.\..*/\1/p' | tail -10 | nl -v 1
echo ""

# Проверка на наличие пауз/блокировок
echo "🔄 ПРОВЕРКА БЛОКИРОВОК И ПАУЗ:"
echo "─────────────────────────────────────────────────────────────"

no_available=$(docker-compose -f docker-compose.prod.yml logs --tail 5000 --since ${HOURS}h parser 2>/dev/null | grep -c "No available proxies" 2>/dev/null)
waiting_count=$(docker-compose -f docker-compose.prod.yml logs --tail 5000 --since ${HOURS}h parser 2>/dev/null | grep -c "waiting.*seconds" 2>/dev/null)
no_available=${no_available:-0}
waiting_count=${waiting_count:-0}

echo "  ⏸️  Пауз из-за отсутствия прокси: $no_available"
echo "  ⏳ Ожиданий прокси: $waiting_count"

if [ "$waiting_count" -gt 0 ] 2>/dev/null; then
    echo ""
    echo "  ⏱️  Последние ожидания прокси:"
    docker-compose -f docker-compose.prod.yml logs --since ${HOURS}h parser 2>/dev/null | grep "waiting.*seconds" | tail -5 | sed 's/^/    /'
fi
echo ""

# Топ проблемных прокси
echo "🔴 ТОП-5 ПРОБЛЕМНЫХ ПРОКСИ (по количеству ошибок):"
echo "─────────────────────────────────────────────────────────────"
docker-compose -f docker-compose.prod.yml logs --tail 3000 --since ${HOURS}h parser 2>/dev/null | grep -E "(Status=40[37]|Timeout.*exceeded)" | sed -n 's/.*proxy=\([^\.]*\)\.\.\..*/\1/p' | sort | uniq -c | sort -rn | head -5 | awk '{printf "  %d ошибок: %s\n", $1, $2}' || echo "  Нет данных"
echo ""

# Рекомендации
echo "💡 РЕКОМЕНДАЦИИ:"
echo "─────────────────────────────────────────────────────────────"

if [ "$timeout_count" -gt 10 ] 2>/dev/null; then
    echo "  ⚠️  Много таймаутов - возможно, нужно увеличить таймаут или проверить прокси"
fi

if [ "$status_403" -gt 20 ] 2>/dev/null; then
    echo "  ⚠️  Много блокировок 403 - CIAN блокирует прокси, возможно нужно увеличить задержки"
fi

if [ "$blocked_proxies" -gt 50 ] 2>/dev/null; then
    echo "  ⚠️  Много блокировок прокси - возможно, нужно увеличить время между запросами"
fi

if [ -n "$success_rate" ] && [ "$(echo "$success_rate < 50" | bc 2>/dev/null || echo "0")" = "1" ] 2>/dev/null; then
    echo "  ⚠️  Низкий процент успешных запросов (<50%) - нужно оптимизировать работу прокси"
fi

if [ "$added_count" -lt 5 ] 2>/dev/null && [ "$status_200" -gt 20 ] 2>/dev/null; then
    echo "  ⚠️  Много успешных запросов, но мало добавлений - возможно, проблема в парсинге (Recjson errors)"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Для просмотра логов в реальном времени:                  ║"
echo "║  docker-compose -f docker-compose.prod.yml logs -f parser ║"
echo "╚════════════════════════════════════════════════════════════╝"

