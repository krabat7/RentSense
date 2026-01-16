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
success=$(docker logs --tail 500 rentsense_parser_1 2>&1 | grep -c "SUCCESS\|New offers added" || echo "0")
captcha=$(docker logs --tail 500 rentsense_parser_1 2>&1 | grep -c "CAPTCHA" || echo "0")
blocked=$(docker logs --tail 500 rentsense_parser_1 2>&1 | grep -c "blocked" || echo "0")
status_403=$(docker logs --tail 500 rentsense_parser_1 2>&1 | grep -c "Status=403" || echo "0")
status_200=$(docker logs --tail 500 rentsense_parser_1 2>&1 | grep -c "Status=200" || echo "0")
connection_error=$(docker logs --tail 500 rentsense_parser_1 2>&1 | grep -c "connection error\|ERR_PROXY" || echo "0")

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
docker exec rentsense_db_1 mysql -u root -proot_password rentsense -e "
SELECT COUNT(*) as total FROM offers;
SELECT COUNT(*) as last_4h FROM offers WHERE created_at >= DATE_SUB(NOW(), INTERVAL 4 HOUR);
SELECT cian_id, price, created_at FROM offers ORDER BY created_at DESC LIMIT 5;
" 2>&1 || echo "[WARN] Не удалось подключиться к БД"
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
if [ "$success" -eq "0" ] && [ "$captcha" -gt "5" ]; then
    echo "[CRITICAL] Проблема: Все прокси возвращают CAPTCHA!"
    echo "   - CIAN агрессивно блокирует прокси"
    echo "   - Нужны более качественные прокси или увеличение задержек"
fi
if [ "$available" -eq "0" ]; then
    echo "[CRITICAL] Проблема: Нет доступных прокси!"
    echo "   - Все прокси заблокированы"
fi
if [ "$status_403" -gt "$status_200" ]; then
    echo "[WARN] Больше 403 ошибок, чем успешных запросов"
    echo "   - CIAN блокирует большинство запросов"
fi
echo

