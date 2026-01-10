# Команды для проверки БД на сервере

## ШАГ 1: Проверить пароль MySQL в .env
```bash
cd /root/rentsense
cat .env | grep MYSQL_ROOT_PASSWORD
```

## ШАГ 2: Проверить подключение к БД через DatabaseManager
```bash
docker exec rentsense_backend_1 python -c "
from app.parser.database import DB
from sqlalchemy import text
try:
    with DB.engine.connect() as conn:
        result = conn.execute(text('SELECT 1 as test'))
        print('✅ Подключение к БД успешно!')
        print(f'Результат: {result.fetchone()}')
except Exception as e:
    print(f'❌ Ошибка подключения: {e}')
"
```

## ШАГ 3: Проверить таблицы в БД (с правильным паролем)
```bash
# Сначала узнайте пароль из .env
MYSQL_PASS=$(grep MYSQL_ROOT_PASSWORD .env | cut -d'=' -f2)
echo "Пароль: $MYSQL_PASS"

# Проверить таблицы
docker exec rentsense_mysql_1 mysql -uroot -p"$MYSQL_PASS" rentsense -e "SHOW TABLES;"
```

## ШАГ 4: Проверить логи parser
```bash
# Подождать немного
sleep 5

# Проверить статус parser
docker-compose -f docker-compose.prod.yml ps parser

# Проверить логи parser
docker-compose -f docker-compose.prod.yml logs parser | tail -50
```

## ШАГ 5: Проверить все сервисы
```bash
docker-compose -f docker-compose.prod.yml ps
```

