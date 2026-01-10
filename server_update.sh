#!/bin/bash
# Скрипт для обновления кода на сервере из Git репозитория

cd /root/rentsense || exit 1

echo "=== Обновление кода из Git репозитория ==="
echo "Время: $(date)"

# Проверяем, что это Git репозиторий
if [ ! -d .git ]; then
    echo "ОШИБКА: Это не Git репозиторий!"
    echo "Выполните: git clone https://github.com/YOUR_USERNAME/RentSense.git /root/rentsense"
    exit 1
fi

# Сохраняем текущую ветку
CURRENT_BRANCH=$(git branch --show-current)
echo "Текущая ветка: $CURRENT_BRANCH"

# Получаем изменения
echo "Получение изменений из репозитория..."
git fetch origin

# Проверяем, есть ли изменения
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/$CURRENT_BRANCH)

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "✓ Код уже актуален, изменений нет"
    exit 0
fi

echo "Обнаружены изменения, обновление..."
git pull origin $CURRENT_BRANCH

if [ $? -eq 0 ]; then
    echo "✓ Код успешно обновлен"
    
    # Перезапускаем контейнеры если нужно
    echo "Перезапуск парсера..."
    docker-compose -f docker-compose.prod.yml restart parser
    
    echo "✓ Готово!"
else
    echo "✗ Ошибка при обновлении кода"
    exit 1
fi

