#!/bin/bash
# Быстрая проверка статуса парсера

cd /root/rentsense || exit 1

echo "🔍 Быстрая проверка парсера"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Статус
STATUS=$(docker-compose -f docker-compose.prod.yml ps parser | tail -1 | awk '{print $4}')
if [ "$STATUS" = "Up" ]; then
    echo "✅ Парсер работает"
else
    echo "❌ Парсер не работает (статус: $STATUS)"
fi
echo ""

# Последняя активность
LAST_ACTIVITY=$(docker-compose -f docker-compose.prod.yml logs --tail=1 parser | tail -1 | cut -d'|' -f1)
echo "🕐 Последняя активность: $LAST_ACTIVITY"
echo ""

# Добавлено за последние 30 минут
ADDED=$(docker-compose -f docker-compose.prod.yml logs --since 30m parser | grep -c "is adding")
echo "📈 Добавлено за 30 мин: $ADDED объявлений"
echo ""

# Ошибки за последние 30 минут
ERRORS=$(docker-compose -f docker-compose.prod.yml logs --since 30m parser | grep -cE "(ERROR|failed|blocked)")
if [ "$ERRORS" -gt 0 ]; then
    echo "⚠️  Ошибок за 30 мин: $ERRORS"
else
    echo "✅ Ошибок нет"
fi
echo ""

# Текущий цикл
CYCLE=$(docker-compose -f docker-compose.prod.yml logs parser | grep "=== Начало цикла парсинга" | tail -1)
if [ -n "$CYCLE" ]; then
    echo "🔄 $CYCLE"
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Для детальной статистики: ./parser_stats.sh"
echo "Для просмотра логов: docker-compose -f docker-compose.prod.yml logs -f parser"

