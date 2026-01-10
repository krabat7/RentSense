#!/bin/bash
# Детальная статистика парсера

cd /root/rentsense || exit 1

echo "╔════════════════════════════════════════════════════════════╗"
echo "║         СТАТИСТИКА ПАРСЕРА RENTSENSE                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Время последнего запуска
echo "📅 Время последнего запуска:"
docker-compose -f docker-compose.prod.yml logs parser | grep "=== Парсер запущен" | tail -1
echo ""

# Текущий цикл
echo "�� Текущий цикл:"
docker-compose -f docker-compose.prod.yml logs parser | grep "=== Начало цикла парсинга" | tail -1
echo ""

# Статистика добавленных объявлений за последний час
echo "📊 Добавленные объявления (последний час):"
added_count=$(docker-compose -f docker-compose.prod.yml logs --since 1h parser | grep -c "is adding")
updated_count=$(docker-compose -f docker-compose.prod.yml logs --since 1h parser | grep -c "is updating")
echo "  ✓ Добавлено новых: $added_count"
echo "  ✓ Обновлено существующих: $updated_count"
echo ""

# Статистика по прокси
echo "🌐 Статистика прокси (последний час):"
blocked_count=$(docker-compose -f docker-compose.prod.yml logs --since 1h parser | grep -c "blocked")
warning_count=$(docker-compose -f docker-compose.prod.yml logs --since 1h parser | grep -c "warning")
unfrozen_count=$(docker-compose -f docker-compose.prod.yml logs --since 1h parser | grep -c "Unfrozen")
echo "  ⚠️  Заблокировано: $blocked_count"
echo "  ⚠️  Предупреждений: $warning_count"
echo "  ✓ Разморожено: $unfrozen_count"
echo ""

# Ошибки парсинга
echo "❌ Ошибки парсинга (последний час):"
failed_count=$(docker-compose -f docker-compose.prod.yml logs --since 1h parser | grep -c "failed")
skipped_line=$(docker-compose -f docker-compose.prod.yml logs --since 1h parser | grep "Skipped:" | tail -1)
skipped_count=$(echo "$skipped_line" | grep -oP 'Skipped: \K\d+' || echo "0")
echo "  ✗ Неудачных попыток: $failed_count"
echo "  ⏭️  Пропущено объявлений: $skipped_count"
echo ""

# Последние успешные добавления
echo "✅ Последние 5 добавленных объявлений:"
docker-compose -f docker-compose.prod.yml logs --since 1h parser | grep "is adding" | tail -5 | sed 's/^/  /'
echo ""

# Последние ошибки
echo "⚠️  Последние 5 ошибок/предупреждений:"
docker-compose -f docker-compose.prod.yml logs --since 1h parser | grep -E "(ERROR|WARNING|failed|blocked)" | tail -5 | sed 's/^/  /'
echo ""

# Статус контейнера
echo "🐳 Статус контейнера:"
docker-compose -f docker-compose.prod.yml ps parser
echo ""

# Использование прокси
echo "📡 Активные прокси (последние запросы):"
docker-compose -f docker-compose.prod.yml logs --since 30m parser | grep "Playwright time" | tail -5 | sed 's/^/  /'
echo ""

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Для просмотра логов в реальном времени:                  ║"
echo "║  docker-compose -f docker-compose.prod.yml logs -f parser ║"
echo "╚════════════════════════════════════════════════════════════╝"
