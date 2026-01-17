#!/bin/bash

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ПРОВЕРКА ADMINER И ПОДКЛЮЧЕНИЯ К MYSQL                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

echo "📋 1. Статус контейнеров:"
echo "────────────────────────────────────────────────────────────"
docker-compose -f docker-compose.prod.yml ps
echo ""

echo "📋 2. Проверка сети Docker:"
echo "────────────────────────────────────────────────────────────"
docker network ls | grep -E "rentsense|bridge"
echo ""

echo "📋 3. Проверка, может ли Adminer разрешить имя 'mysql':"
echo "────────────────────────────────────────────────────────────"
ADMINER_CONTAINER=$(docker-compose -f docker-compose.prod.yml ps -q adminer)
if [ -n "$ADMINER_CONTAINER" ]; then
    echo "Контейнер Adminer найден: $ADMINER_CONTAINER"
    docker exec $ADMINER_CONTAINER ping -c 2 mysql 2>&1 | head -5
else
    echo "❌ Контейнер Adminer не найден!"
fi
echo ""

echo "📋 4. IP-адрес контейнера MySQL:"
echo "────────────────────────────────────────────────────────────"
MYSQL_CONTAINER=$(docker-compose -f docker-compose.prod.yml ps -q mysql)
if [ -n "$MYSQL_CONTAINER" ]; then
    echo "Контейнер MySQL найден: $MYSQL_CONTAINER"
    docker inspect $MYSQL_CONTAINER | grep -A 5 "IPAddress" | head -10
else
    echo "❌ Контейнер MySQL не найден!"
fi
echo ""

echo "📋 5. Правильный URL для подключения:"
echo "────────────────────────────────────────────────────────────"
echo "Попробуйте один из вариантов:"
echo ""
echo "Вариант 1 (имя сервиса):"
echo "http://89.110.92.128:8080/?server=mysql&username=rentsense&db=rentsense"
echo ""
echo "Вариант 2 (если не работает, используйте IP контейнера):"
if [ -n "$MYSQL_CONTAINER" ]; then
    MYSQL_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $MYSQL_CONTAINER)
    echo "http://89.110.92.128:8080/?server=$MYSQL_IP&username=rentsense&db=rentsense"
    echo ""
    echo "Вариант 3 (localhost, если Adminer и MySQL на одном хосте):"
    echo "http://89.110.92.128:8080/?server=127.0.0.1&username=rentsense&db=rentsense"
else
    echo "(IP контейнера не найден)"
fi
echo ""

echo "📋 6. Пароль для пользователя rentsense:"
echo "────────────────────────────────────────────────────────────"
echo "Проверьте переменную окружения MYSQL_PASSWORD в .env файле"
echo "или используйте root пароль: MYSQL_ROOT_PASSWORD"
echo ""

echo "💡 РЕШЕНИЕ:"
echo "────────────────────────────────────────────────────────────"
echo "Если имя 'mysql' не работает, попробуйте:"
echo "1. Перезапустить контейнеры: docker-compose -f docker-compose.prod.yml restart adminer mysql"
echo "2. Использовать IP-адрес контейнера MySQL (см. выше)"
echo "3. Проверить, что оба контейнера в одной сети Docker"


