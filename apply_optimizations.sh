#!/bin/bash
# Скрипт для применения оптимизаций парсера на сервере

cd /root/rentsense || exit 1

echo "=== Применение оптимизаций парсера ==="
echo ""

# 1. Оптимизация задержек в app/parser/main.py
echo "1. Оптимизация задержек в main.py..."

# Замена time.sleep(5) на time.sleep(2) (два места)
sed -i 's/time\.sleep(5)  # Уменьшено с 5 до 2 секунд для ускорения/time.sleep(2)  # Уменьшено с 5 до 2 секунд для ускорения/g' app/parser/main.py
sed -i 's/time\.sleep(5)$/time.sleep(2)  # Уменьшено с 5 до 2 секунд для ускорения/g' app/parser/main.py

# Замена 45 секунд на 20 секунд после успешного запроса
sed -i 's/proxyDict\[proxy\] = time\.time() + 45$/proxyDict[proxy] = time.time() + 20  # Оптимизировано с 45 до 20 секунд/g' app/parser/main.py
sed -i 's/proxyDict\[proxy\] = time\.time() + 45/proxyDict[proxy] = time.time() + 20/g' app/parser/main.py

# Оптимизация логики ожидания прокси (меняем < 2 на < 1 и добавляем ограничение 60 секунд)
sed -i 's/if len(available_proxies) < 2:/if len(available_proxies) < 1:/g' app/parser/main.py
sed -i 's/count = min(len(proxyDict) - 1, 2)/count = min(len(proxyDict) - 1, 1)/g' app/parser/main.py
sed -i 's/misstime = mintime - timenow/misstime = min(mintime - timenow, 60)  # Максимум 60 секунд/g' app/parser/main.py

# 2. Оптимизация интервала между циклами в app/scheduler/crontab.py
echo "2. Оптимизация интервала между циклами в crontab.py..."
sed -i 's/PARSE_INTERVAL = 3600/PARSE_INTERVAL = 1800  # 30 минут (уменьшено с 60 для ускорения)/g' app/scheduler/crontab.py

echo ""
echo "=== Оптимизации применены ==="
echo ""
echo "Изменения:"
echo "- Задержка после успешного запроса: 45 -> 20 секунд"
echo "- Задержки внутри запроса: 5+5 -> 2+2 секунды"
echo "- Интервал между циклами: 60 -> 30 минут"
echo "- Ожидание прокси: минимум 2 -> 1, максимум 60 секунд"
echo ""
echo "Перезапускаем парсер..."
docker-compose -f docker-compose.prod.yml restart parser
echo ""
echo "✓ Парсер перезапущен с оптимизациями!"
echo ""
echo "Проверьте логи через несколько минут:"
echo "  docker-compose -f docker-compose.prod.yml logs --tail=50 parser"

