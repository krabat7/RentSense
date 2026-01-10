#!/bin/bash
cd /root/rentsense || exit 1
echo "=== Обновление кода из GitHub ==="
echo "Время: $(date)"

# Получаем изменения
git fetch origin

# Проверяем, есть ли изменения
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "✓ Код уже актуален, изменений нет"
    exit 0
fi

echo "Обнаружены изменения, обновление..."
git pull origin main

if [ $? -eq 0 ]; then
    echo "✓ Код успешно обновлен"
    
    # Перезапускаем парсер
    echo "Перезапуск парсера..."
    docker-compose -f docker-compose.prod.yml restart parser
    
    echo "✓ Готово!"
else
    echo "✗ Ошибка при обновлении кода"
    exit 1
fi
