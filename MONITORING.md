# Мониторинг парсера RentSense

## Быстрая проверка статуса

```bash
cd /root/rentsense && \
echo "=== Быстрая проверка парсера ===" && \
echo "Статус:" && \
docker-compose -f docker-compose.prod.yml ps parser | tail -1 && \
echo "" && \
echo "Добавлено за последние 100 строк логов:" && \
docker-compose -f docker-compose.prod.yml logs --tail=100 parser | grep -c "is adding" && \
echo "" && \
echo "Ошибок прокси (403/captcha/blocked):" && \
docker-compose -f docker-compose.prod.yml logs --tail=100 parser | grep -cE "(403|blocked|captcha)" && \
echo "" && \
echo "Последние 5 добавленных объявлений:" && \
docker-compose -f docker-compose.prod.yml logs --tail=200 parser | grep "is adding" | tail -5
```

## Детальная статистика

```bash
cd /root/rentsense && \
echo "╔════════════════════════════════════════════════════════════╗" && \
echo "║         СТАТИСТИКА ПАРСЕРА (последние 500 строк)          ║" && \
echo "╚════════════════════════════════════════════════════════════╝" && \
echo "" && \
echo "📊 Добавлено новых объявлений:" && \
docker-compose -f docker-compose.prod.yml logs --tail=500 parser | grep -c "is adding" && \
echo "" && \
echo "🌐 Ошибки прокси (403/captcha/blocked):" && \
docker-compose -f docker-compose.prod.yml logs --tail=500 parser | grep -cE "(403|blocked|captcha)" && \
echo "" && \
echo "⚠️  Пропущено объявлений (failed attempts):" && \
docker-compose -f docker-compose.prod.yml logs --tail=500 parser | grep -c "failed, will retry" && \
echo "" && \
echo "✅ Последние 10 успешных добавлений:" && \
docker-compose -f docker-compose.prod.yml logs --tail=500 parser | grep "is adding" | tail -10 && \
echo "" && \
echo "❌ Последние 10 ошибок:" && \
docker-compose -f docker-compose.prod.yml logs --tail=500 parser | grep -E "(ERROR|403|blocked)" | tail -10
```

## Проверка использования прокси

```bash
cd /root/rentsense && \
echo "=== Использование прокси (последние 200 строк) ===" && \
docker-compose -f docker-compose.prod.yml logs --tail=200 parser | grep "Playwright time" | tail -10 && \
echo "" && \
echo "=== Заблокированные прокси ===" && \
docker-compose -f docker-compose.prod.yml logs --tail=500 parser | grep -E "(blocked|warning)" | tail -10
```

## Полная статистика цикла

```bash
cd /root/rentsense && \
echo "=== Статистика последнего цикла ===" && \
docker-compose -f docker-compose.prod.yml logs --tail=1000 parser | grep -E "(=== Начало цикла|Added:|Skipped:|=== Цикл.*завершен)" | tail -5 && \
echo "" && \
echo "=== Детали последнего цикла ===" && \
docker-compose -f docker-compose.prod.yml logs --tail=1000 parser | grep -A 1 "Apart pages.*is END" | tail -2
```

## Логи в реальном времени

```bash
docker-compose -f docker-compose.prod.yml logs -f parser
```

## Установка скриптов мониторинга

Создайте файлы на сервере для удобного использования.

