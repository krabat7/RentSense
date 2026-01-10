#!/bin/bash
# Применение оптимизаций v2: убрать интервал 30 минут и увеличить задержку до 28 секунд

cd /root/rentsense || exit 1

echo "=== Применение оптимизаций v2 ==="
echo ""

# 1. Убрать интервал 30 минут (сделать 60 секунд)
echo "1. Убираем интервал 30 минут..."
sed -i 's/PARSE_INTERVAL = 1800/PARSE_INTERVAL = 60  # 1 минута (уменьшено с 30 минут)/g' app/scheduler/crontab.py
sed -i 's/PARSE_INTERVAL = 3600/PARSE_INTERVAL = 60/g' app/scheduler/crontab.py

# Обновляем логику ожидания
if ! grep -q "if PARSE_INTERVAL > 0:" app/scheduler/crontab.py; then
    sed -i 's/logging.info(f"Ожидание {PARSE_INTERVAL} секунд/logging.info(f"Короткая пауза {PARSE_INTERVAL} секунд/g' app/scheduler/crontab.py
    # Добавляем проверку на 0
    sed -i 's/await asyncio.sleep(PARSE_INTERVAL)/if PARSE_INTERVAL > 0:\n            await asyncio.sleep(PARSE_INTERVAL)\n        else:\n            logging.info("Переход к следующему циклу без паузы...")/g' app/scheduler/crontab.py
fi

echo "✓ Интервал уменьшен до 60 секунд"
echo ""

# 2. Увеличить задержку до 28 секунд
echo "2. Увеличиваем задержку до 28 секунд..."
sed -i 's/time\.time() + 20$/time.time() + 28  # Увеличено с 20 на основе анализа/g' app/parser/main.py
sed -i 's/time\.time() + 20  # Оптимизировано/time.time() + 28  # Увеличено с 20 на основе анализа/g' app/parser/main.py
sed -i 's/20 секунд (было 45)/28 секунд (увеличено с 20 на основе анализа - 56% ошибок)/g' app/parser/main.py

echo "✓ Задержка увеличена до 28 секунд"
echo ""

# 3. Применить исправление IndexError (если еще не применено)
echo "3. Проверяем исправление IndexError..."
if grep -q "random.choice.*proxyDict.items()" app/parser/main.py; then
    echo "Применяем исправление IndexError..."
    python3 << 'PYEOF'
import re

with open('app/parser/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

if "proxy = random.choice([k for k, v in proxyDict.items() if v <= time.time()])" in content:
    old = """    else:
        # Если все прокси заблокированы, используем случайный (fallback)
        proxy = random.choice([k for k, v in proxyDict.items() if v <= time.time()])"""
    
    new = """    else:
        # Если все прокси заблокированы после ожидания, используем пустой прокси (без прокси)
        # или выбираем тот, который освободится раньше всех
        if len(proxyDict) > 1:  # Есть прокси в словаре
            # Выбираем прокси с наименьшим временем блокировки (освободится раньше всех)
            earliest_proxy = min(proxyDict.items(), key=lambda x: x[1])
            if earliest_proxy[1] <= time.time() + 300:  # Если освободится в течение 5 минут
                proxy = earliest_proxy[0]
                logging.warning(f'All proxies blocked, using earliest available: {proxy[:30]}... (unlocks in {earliest_proxy[1] - time.time():.0f}s)')
            else:
                # Если все прокси заблокированы надолго, используем пустой прокси
                proxy = ''
                logging.warning('All proxies blocked for >5 minutes, using no proxy')
        else:
            # Нет прокси в словаре, используем пустой
            proxy = ''
            logging.warning('No proxies configured, using no proxy')"""
    
    content = content.replace(old, new)
    with open('app/parser/main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Исправление IndexError применено")
else:
    print("✓ Исправление IndexError уже применено")
PYEOF
else
    echo "✓ Исправление IndexError уже применено"
fi
echo ""

# 4. Перезапустить парсер
echo "4. Перезапускаем парсер..."
docker-compose -f docker-compose.prod.yml restart parser

echo ""
echo "=== Оптимизации применены ==="
echo ""
echo "Изменения:"
echo "  - Интервал между циклами: 30 минут -> 60 секунд"
echo "  - Задержка после успешного запроса: 20 секунд -> 28 секунд"
echo "  - Исправление IndexError применено"
echo ""
echo "Проверьте логи через минуту:"
echo "  docker-compose -f docker-compose.prod.yml logs --tail=30 parser"

