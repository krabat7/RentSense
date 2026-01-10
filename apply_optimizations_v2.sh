#!/bin/bash
cd /root/rentsense || exit 1

echo "=== Применение оптимизаций v2 ==="
echo ""

# 1. Убрать интервал 30 минут (сделать 60 секунд)
echo "1. Убираем интервал 30 минут..."
sed -i 's/PARSE_INTERVAL = 1800/PARSE_INTERVAL = 60  # 1 минута (уменьшено с 30 минут)/g' app/scheduler/crontab.py

# Обновляем логику ожидания
if ! grep -q "if PARSE_INTERVAL > 0:" app/scheduler/crontab.py; then
    sed -i 's/logging.info(f"Ожидание {PARSE_INTERVAL} секунд/logging.info(f"Короткая пауза {PARSE_INTERVAL} секунд/g' app/scheduler/crontab.py
fi

echo "✓ Интервал уменьшен до 60 секунд"
echo ""

# 2. Увеличить задержку до 28 секунд
echo "2. Увеличиваем задержку до 28 секунд..."
sed -i 's/time\.time() + 20$/time.time() + 28  # Увеличено с 20 на основе анализа/g' app/parser/main.py
sed -i 's/time\.time() + 20  # Оптимизировано/time.time() + 28  # Увеличено с 20 на основе анализа/g' app/parser/main.py
sed -i 's/20 секунд (было 45)/28 секунд (увеличено с 20 на основе анализа)/g' app/parser/main.py

echo "✓ Задержка увеличена до 28 секунд"
echo ""

# 3. Перезапустить парсер
echo "3. Перезапускаем парсер..."
docker-compose -f docker-compose.prod.yml restart parser

echo ""
echo "=== Оптимизации применены ==="
echo "Изменения:"
echo "  - Интервал между циклами: 30 минут -> 60 секунд"
echo "  - Задержка после успешного запроса: 20 секунд -> 28 секунд"
