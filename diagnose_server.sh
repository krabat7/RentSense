#!/bin/bash
# Диагностика парсера на сервере

echo "================================================================================="
echo "КОМПЛЕКСНАЯ ДИАГНОСТИКА ПАРСЕРА НА СЕРВЕРЕ"
echo "================================================================================="
echo

# 1. Статус парсера
echo "[1] Статус парсера:"
docker ps --filter name=parser --format "{{.Status}}" || echo "[ERROR] Парсер не запущен"
echo

# 2. Последние логи
echo "[2] Последние 50 строк логов парсера:"
docker logs --tail 50 rentsense_parser_1 2>&1 | tail -20
echo

# 3. Ошибки в логах
echo "[3] Ошибки в последних 200 строках:"
docker logs --tail 200 rentsense_parser_1 2>&1 | grep -E "(ERROR|Exception|Traceback|CAPTCHA|403|blocked)" | tail -10
echo

# 4. Статистика по ключевым словам
echo "[4] Статистика за последние 500 строк:"
total_lines=$(docker logs --tail 500 rentsense_parser_1 2>&1 | wc -l)
success=$(docker logs --tail 500 rentsense_parser_1 2>&1 | grep -c "SUCCESS\|New offers added" 2>/dev/null || echo "0")
captcha=$(docker logs --tail 500 rentsense_parser_1 2>&1 | grep -c "CAPTCHA" 2>/dev/null || echo "0")
blocked=$(docker logs --tail 500 rentsense_parser_1 2>&1 | grep -c "blocked" 2>/dev/null || echo "0")
status_403=$(docker logs --tail 500 rentsense_parser_1 2>&1 | grep -c "Status=403" 2>/dev/null || echo "0")
status_200=$(docker logs --tail 500 rentsense_parser_1 2>&1 | grep -c "Status=200" 2>/dev/null || echo "0")
connection_error=$(docker logs --tail 500 rentsense_parser_1 2>&1 | grep -c "connection error\|ERR_PROXY" 2>/dev/null || echo "0")

# Убираем переносы строк из переменных
success=$(echo "$success" | tr -d '\n' | head -1)
captcha=$(echo "$captcha" | tr -d '\n' | head -1)
blocked=$(echo "$blocked" | tr -d '\n' | head -1)
status_403=$(echo "$status_403" | tr -d '\n' | head -1)
status_200=$(echo "$status_200" | tr -d '\n' | head -1)
connection_error=$(echo "$connection_error" | tr -d '\n' | head -1)

echo "   Всего строк логов: $total_lines"
echo "   Успешных добавлений: $success"
echo "   CAPTCHA обнаружено: $captcha"
echo "   Блокировок прокси: $blocked"
echo "   Статус 403: $status_403"
echo "   Статус 200: $status_200"
echo "   Ошибок подключения: $connection_error"
echo

# 5. Проверка базы данных
echo "[5] Проверка базы данных:"
# Пытаемся найти контейнер БД
db_container=$(docker ps --format "{{.Names}}" | grep -E "(db|mysql|database)" | head -1)
if [ -z "$db_container" ]; then
    echo "[WARN] Контейнер БД не найден. Проверяю все контейнеры:"
    docker ps --format "{{.Names}}"
    db_container=""
else
    echo "   Найден контейнер БД: $db_container"
    docker exec "$db_container" mysql -u root -proot_password rentsense -e "
    SELECT COUNT(*) as total FROM offers;
    SELECT COUNT(*) as last_4h FROM offers WHERE created_at >= DATE_SUB(NOW(), INTERVAL 4 HOUR);
    SELECT cian_id, price, created_at FROM offers ORDER BY created_at DESC LIMIT 5;
    " 2>&1 || echo "[WARN] Не удалось подключиться к БД"
fi
echo

# 6. Последние действия парсера
echo "[6] Последние действия парсера:"
docker logs --tail 100 rentsense_parser_1 2>&1 | grep -E "(Starting parsing|Finished|SUCCESS|find_start_page|process_page)" | tail -10
echo

# 7. Проверка прокси (через Python)
echo "[7] Статус прокси:"
docker exec rentsense_parser_1 python3 -c "
from app.parser.tools import proxyDict, proxyErrorCount, proxyConnectionErrors
import time
current = time.time()
total = len([p for p in proxyDict.keys() if p != ''])
available = len([k for k, v in proxyDict.items() if v <= current and k != ''])
blocked = len([k for k, v in proxyDict.items() if v > current and k != ''])
print(f'   Всего прокси: {total}')
print(f'   Доступно: {available}')
print(f'   Заблокировано: {blocked}')
if blocked > 0:
    blocked_proxies = {k: v for k, v in proxyDict.items() if v > current and k != ''}
    min_unlock = min(blocked_proxies.values()) if blocked_proxies else current
    unlock_time = (min_unlock - current) / 60
    print(f'   Самый ранний разблокируется через: {unlock_time:.1f} минут')
" 2>&1 || echo "[WARN] Не удалось проверить статус прокси"
echo

echo "================================================================================="
echo "АНАЛИЗ:"
echo "================================================================================="
echo
# Проверяем, что переменные - числа (используем только числовые проверки)
if [ -n "$success" ] && [ -n "$captcha" ]; then
    success_num=$(echo "$success" | tr -d '[:space:]' | head -1)
    captcha_num=$(echo "$captcha" | tr -d '[:space:]' | head -1)
    
    if [ "$success_num" -eq "0" ] 2>/dev/null && [ "$captcha_num" -gt "5" ] 2>/dev/null; then
        echo "[CRITICAL] Проблема: Все прокси возвращают CAPTCHA!"
        echo "   - CIAN агрессивно блокирует прокси"
        echo "   - Нужны более качественные прокси или увеличение задержек"
        echo "   - Статистика: $captcha_num CAPTCHA, $success_num успешных добавлений"
    fi
    
    if [ "$captcha_num" -gt "100" ] 2>/dev/null; then
        echo "[CRITICAL] Очень много CAPTCHA ($captcha_num за последние 500 строк)"
        echo "   - Все прокси заблокированы CIAN"
        echo "   - Рекомендуется: увеличить задержки или заменить прокси"
    fi
fi

if [ -n "$status_403" ] && [ -n "$status_200" ]; then
    status_403_num=$(echo "$status_403" | tr -d '[:space:]' | head -1)
    status_200_num=$(echo "$status_200" | tr -d '[:space:]' | head -1)
    
    if [ "$status_403_num" -gt "$status_200_num" ] 2>/dev/null; then
        echo "[WARN] Больше 403 ошибок ($status_403_num), чем успешных запросов ($status_200_num)"
        echo "   - CIAN блокирует большинство запросов"
    fi
fi
echo

