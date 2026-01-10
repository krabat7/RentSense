# Финальная проверка статуса всех сервисов

## Команды для выполнения на сервере:

```bash
cd /root/rentsense

# 1. Проверить статус всех сервисов
docker-compose -f docker-compose.prod.yml ps

# 2. Проверить, что parser процесс запущен
docker exec rentsense_parser_1 ps aux | grep python

# 3. Проверить health endpoint backend
curl http://localhost:8000/health

# 4. Проверить подключение к БД из parser
docker exec rentsense_parser_1 python -c "
from app.parser.database import DB
from sqlalchemy import text
try:
    with DB.engine.connect() as conn:
        result = conn.execute(text('SELECT COUNT(*) FROM offers'))
        count = result.fetchone()[0]
        print(f'✅ Parser подключен к БД!')
        print(f'Количество записей в offers: {count}')
except Exception as e:
    print(f'❌ Ошибка: {e}')
"

# 5. Проверить логи всех сервисов (последние 10 строк)
echo "=== Backend logs ==="
docker-compose -f docker-compose.prod.yml logs backend | tail -10

echo "=== Parser logs ==="
docker-compose -f docker-compose.prod.yml logs parser | tail -10

echo "=== MySQL logs ==="
docker-compose -f docker-compose.prod.yml logs mysql | tail -10
```

## Ожидаемые результаты:

✅ **Backend**: `Up (healthy)` - работает, health endpoint отвечает  
✅ **MySQL**: `Up (healthy)` - работает, таблицы созданы  
✅ **Parser**: `Up` - работает, ждет времени выполнения cron задачи (00:00 каждый день)

## Следующие шаги:

1. ✅ Backend запущен и работает
2. ✅ MySQL запущен, таблицы созданы
3. ✅ Parser запущен и ждет выполнения задачи
4. ⏳ Настроить автоматические бэкапы в Yandex Object Storage (TODO #6)
5. ⏳ Протестировать парсинг вручную (можно запустить тестовый парсинг)

