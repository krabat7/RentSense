#!/bin/bash
# Статистика парсера за последние 24 часа и общая статистика БД

echo "╔════════════════════════════════════════════════════════════╗"
echo "║    СТАТИСТИКА ПАРСЕРА ЗА ПОСЛЕДНИЕ 24 ЧАСА                ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Проверяем, что мы в правильной директории
if [ ! -f "docker-compose.prod.yml" ]; then
    echo "❌ Файл docker-compose.prod.yml не найден"
    echo "   Перейдите в директорию /root/rentsense"
    exit 1
fi

# Статистика из логов за последние 24 часа
echo "📊 СТАТИСТИКА ИЗ ЛОГОВ (последние 24 часа):"
echo "─────────────────────────────────────────────────────────────"

added_24h=$(docker-compose -f docker-compose.prod.yml logs --since 24h parser 2>/dev/null | grep -c "is adding" 2>/dev/null || echo "0")
updated_24h=$(docker-compose -f docker-compose.prod.yml logs --since 24h parser 2>/dev/null | grep -c "is updating" 2>/dev/null || echo "0")
photos_24h=$(docker-compose -f docker-compose.prod.yml logs --since 24h parser 2>/dev/null | grep -c "added.*photos" 2>/dev/null || echo "0")

echo "  ✓ Добавлено новых объявлений: $added_24h"
echo "  ✓ Обновлено существующих: $updated_24h"
echo "  📷 Добавлено фото: $photos_24h"
echo ""

# Статистика из базы данных
echo "📈 СТАТИСТИКА ИЗ БАЗЫ ДАННЫХ:"
echo "─────────────────────────────────────────────────────────────"

# Пытаемся получить данные из БД
if [ -f ".env" ]; then
    source .env
    
    DB_STATS=$(docker-compose -f docker-compose.prod.yml exec -T db mysql -u"$DB_LOGIN" -p"$DB_PASS" "$DB_NAME" -sN -e "
        SELECT 
            (SELECT COUNT(*) FROM offers) as total_offers,
            (SELECT COUNT(*) FROM offers WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)) as offers_24h,
            (SELECT COUNT(*) FROM photos) as total_photos,
            (SELECT COUNT(*) FROM photos WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)) as photos_24h;
    " 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$DB_STATS" ]; then
        echo "$DB_STATS" | awk -F'\t' '{
            print "  📦 Всего объявлений в БД: " $1
            print "  📦 Добавлено за 24 часа: " $2
            print "  📷 Всего фото в БД: " $3
            print "  📷 Добавлено фото за 24 часа: " $4
        }'
    else
        echo "  ⚠️  Не удалось получить данные из БД через docker exec"
        echo "  💡 Используйте Adminer или выполните SQL-запрос вручную (см. ниже)"
    fi
else
    echo "  ⚠️  Файл .env не найден"
fi

echo ""
echo "💡 Для проверки БД через Adminer (http://YOUR_SERVER_IP:8080) используйте запрос:"
echo "─────────────────────────────────────────────────────────────"
cat << 'SQL_QUERY'
SELECT 
    (SELECT COUNT(*) FROM offers) as total_offers,
    (SELECT COUNT(*) FROM offers WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)) as offers_24h,
    (SELECT COUNT(*) FROM photos) as total_photos,
    (SELECT COUNT(*) FROM photos WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)) as photos_24h;
SQL_QUERY
echo ""

# Последние добавленные объявления из логов
echo "✅ ПОСЛЕДНИЕ 10 ДОБАВЛЕННЫХ ОБЪЯВЛЕНИЙ (24 часа):"
echo "─────────────────────────────────────────────────────────────"
docker-compose -f docker-compose.prod.yml logs --since 24h parser 2>/dev/null | grep "is adding" | tail -10 | sed 's/^/  /' || echo "  Нет данных"
echo ""

# Ошибки и предупреждения
echo "⚠️  ОШИБКИ И ПРЕДУПРЕЖДЕНИЯ (последние 24 часа):"
echo "─────────────────────────────────────────────────────────────"
errors_24h=$(docker-compose -f docker-compose.prod.yml logs --since 24h parser 2>/dev/null | grep -cE "(ERROR|error)" 2>/dev/null || echo "0")
warnings_24h=$(docker-compose -f docker-compose.prod.yml logs --since 24h parser 2>/dev/null | grep -cE "(WARNING|warning)" 2>/dev/null || echo "0")
echo "  ❌ Ошибок: $errors_24h"
echo "  ⚠️  Предупреждений: $warnings_24h"
echo ""

# Статус парсера
echo "🔄 СТАТУС ПАРСЕРА:"
echo "─────────────────────────────────────────────────────────────"
if docker-compose -f docker-compose.prod.yml ps parser | grep -q "Up"; then
    echo "  ✓ Парсер работает"
    uptime=$(docker-compose -f docker-compose.prod.yml ps parser | grep parser | awk '{print $4, $5, $6, $7}' || echo "неизвестно")
    echo "  ⏱️  Время работы: $uptime"
else
    echo "  ❌ Парсер не работает!"
fi
echo ""

# Последние логи (последняя активность)
echo "📋 ПОСЛЕДНЯЯ АКТИВНОСТЬ (последние 5 строк):"
echo "─────────────────────────────────────────────────────────────"
docker-compose -f docker-compose.prod.yml logs --tail 5 parser 2>/dev/null | sed 's/^/  /' || echo "  Нет данных"
echo ""

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Для детальной статистики используйте:                     ║"
echo "║  ./parser_stats.sh                                          ║"
echo "╚════════════════════════════════════════════════════════════╝"

