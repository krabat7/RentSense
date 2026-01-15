#!/bin/bash

# Скрипт для анализа причин замедления парсинга

echo "=== Анализ причин замедления парсинга ==="
echo ""

# Проверка статуса контейнера
echo "1. Статус парсера:"
docker ps --filter "name=parser" --format "table {{.Names}}\t{{.Status}}\t{{.RunningFor}}" 2>/dev/null || echo "Контейнер не найден"
echo ""

# Последние сообщения о циклах
echo "2. Последние циклы парсинга (последние 10):"
timeout 10 docker logs rentsense_parser_1 2>&1 | grep -E "(Начало цикла|Цикл.*завершен|превысил максимальное время)" | tail -10
echo ""

# Статистика по фильтрации dailyFlatRent
echo "3. Фильтрация посуточной аренды (dailyFlatRent):"
daily_rent_count=$(timeout 10 docker logs rentsense_parser_1 2>&1 | grep -c "category=dailyFlatRent" || echo "0")
echo "   Отфильтровано посуточной аренды: $daily_rent_count"
echo ""

# Статистика по добавленным объявлениям
echo "4. Статистика добавленных объявлений (последние 24 часа):"
added_24h=$(timeout 10 docker logs rentsense_parser_1 2>&1 | grep -c "Apart page.*is adding" || echo "0")
added_last_hour=$(timeout 10 docker logs rentsense_parser_1 2>&1 | grep "$(date -u +'%Y-%m-%d %H')" | grep -c "Apart page.*is adding" || echo "0")
echo "   Добавлено за 24 часа: $added_24h"
echo "   Добавлено за последний час: $added_last_hour"
echo ""

# Статистика по ошибкам
echo "5. Статистика ошибок (последние 24 часа):"
timeouts_24h=$(timeout 10 docker logs rentsense_parser_1 2>&1 | grep -c "Timeout.*exceeded" || echo "0")
errors_403=$(timeout 10 docker logs rentsense_parser_1 2>&1 | grep -c "Status: 403" || echo "0")
errors_407=$(timeout 10 docker logs rentsense_parser_1 2>&1 | grep -c "Status: 407" || echo "0")
recjson_errors=$(timeout 10 docker logs rentsense_parser_1 2>&1 | grep -c "Recjson not match" || echo "0")
echo "   Таймауты: $timeouts_24h"
echo "   Ошибки 403: $errors_403"
echo "   Ошибки 407: $errors_407"
echo "   Ошибки Recjson: $recjson_errors"
echo ""

# Статистика по пустым страницам
echo "6. Пустые страницы (последние 24 часа):"
empty_pages=$(timeout 10 docker logs rentsense_parser_1 2>&1 | grep -c "Empty page" || echo "0")
echo "   Пустых страниц: $empty_pages"
echo ""

# Статистика по достижению конца списка
echo "7. Достижение конца списка (последние 24 часа):"
end_reached=$(timeout 10 docker logs rentsense_parser_1 2>&1 | grep -c "End of.*reached\|3 consecutive empty pages" || echo "0")
echo "   Достигнут конец списка: $end_reached раз"
echo ""

# Статистика по комбинациям room/sort
echo "8. Обработка комбинаций (последние 10):"
timeout 10 docker logs rentsense_parser_1 2>&1 | grep -E "(Starting parsing|Finished: room)" | tail -10
echo ""

# Последние ошибки
echo "9. Последние ошибки (последние 10):"
timeout 10 docker logs rentsense_parser_1 2>&1 | grep -E "(ERROR|WARNING)" | tail -10
echo ""

# Анализ скорости парсинга
echo "10. Анализ скорости парсинга:"
last_cycle_start=$(timeout 10 docker logs rentsense_parser_1 2>&1 | grep "Начало цикла" | tail -1 | awk '{print $1, $2}')
last_cycle_end=$(timeout 10 docker logs rentsense_parser_1 2>&1 | grep -E "(Цикл.*завершен|превысил максимальное время)" | tail -1 | awk '{print $1, $2}')

if [ -n "$last_cycle_start" ] && [ -n "$last_cycle_end" ]; then
    echo "   Последний цикл начался: $last_cycle_start"
    echo "   Последний цикл завершился: $last_cycle_end"
else
    echo "   Не удалось определить время циклов"
fi
echo ""

# Рекомендации
echo "=== Рекомендации ==="
if [ "$empty_pages" -gt 100 ]; then
    echo "⚠️  Много пустых страниц - возможно, парсер быстро доходит до конца списка"
fi

if [ "$end_reached" -gt 50 ]; then
    echo "⚠️  Парсер часто достигает конца списка - возможно, новых объявлений мало"
fi

if [ "$timeouts_24h" -gt 100 ]; then
    echo "⚠️  Много таймаутов - возможно, проблемы с прокси или сетью"
fi

if [ "$errors_403" -gt 200 ]; then
    echo "⚠️  Много ошибок 403 - возможно, прокси заблокированы"
fi

if [ "$added_last_hour" -lt 5 ]; then
    echo "⚠️  За последний час добавлено мало объявлений - проверьте логи на ошибки"
fi

echo ""
echo "=== Анализ завершен ==="

