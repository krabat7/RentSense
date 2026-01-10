# Следующие шаги на сервере

## Что уже сделано ✅
- Docker установлен и запущен
- Скрипты скопированы
- Директории созданы

## Что нужно сделать дальше

### Шаг 1: Установить недостающую зависимость

На сервере выполните:
```bash
apt install -y libasound2t64 libnss3 libnspr4 libatk1.0-0t64 libatk-bridge2.0-0t64 libcups2t64 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 wget git
```

### Шаг 2: Проверить, какие файлы скопировались

```bash
cd /root/rentsense
ls -la
```

Если нет директорий `app`, `ml`, `tests` или файлов `docker-compose.prod.yml`, `Dockerfile`, `requirements.txt` - их нужно скопировать.

### Шаг 3: Скопировать недостающие файлы (на вашем компьютере в PowerShell)

```powershell
cd F:\hw_hse\Diploma\RentSense

# Копировать основные файлы и директории
scp -r app root@89.110.92.128:/root/rentsense/
# Пароль: D68v9kz3mL21a!FRZm23

scp -r ml root@89.110.92.128:/root/rentsense/
# Пароль: D68v9kz3mL21a!FRZm23

scp -r tests root@89.110.92.128:/root/rentsense/
# Пароль: D68v9kz3mL21a!FRZm23

scp docker-compose.prod.yml root@89.110.92.128:/root/rentsense/
# Пароль: D68v9kz3mL21a!FRZm23

scp Dockerfile root@89.110.92.128:/root/rentsense/
# Пароль: D68v9kz3mL21a!FRZm23

scp requirements.txt root@89.110.92.128:/root/rentsense/
# Пароль: D68v9kz3mL21a!FRZm23

scp create_database.py root@89.110.92.128:/root/rentsense/
# Пароль: D68v9kz3mL21a!FRZm23

scp .env.server root@89.110.92.128:/root/rentsense/.env
# Пароль: D68v9kz3mL21a!FRZm23
```

### Шаг 4: Настроить .env на сервере

```bash
cd /root/rentsense
nano .env
```

Замените `CHANGE_THIS_TO_STRONG_PASSWORD` (2 раза) на надежный пароль, например: `RentSense2025!Secure`

Сохраните: `Ctrl+X`, затем `Y`, затем `Enter`

### Шаг 5: Проверить наличие Docker Compose

```bash
docker-compose --version
```

Если команда не найдена, установите:
```bash
apt install -y docker-compose
```

### Шаг 6: Запустить Docker Compose

```bash
cd /root/rentsense
docker-compose -f docker-compose.prod.yml up -d --build
```

Это займет несколько минут - будет собираться образ и запускаться контейнеры.

### Шаг 7: Подождать запуска MySQL (60 секунд)

```bash
sleep 60
```

### Шаг 8: Инициализировать БД

```bash
docker-compose -f docker-compose.prod.yml exec backend python create_database.py
docker-compose -f docker-compose.prod.yml exec backend python -m app.parser.init_db
```

### Шаг 9: Проверка

```bash
# Проверить контейнеры
docker-compose -f docker-compose.prod.yml ps

# Проверить таблицы в БД (замените YOUR_PASSWORD на пароль из .env)
docker-compose -f docker-compose.prod.yml exec mysql mysql -uroot -pYOUR_PASSWORD rentsense -e "SHOW TABLES;"

# Тест парсера
docker-compose -f docker-compose.prod.yml exec backend python -c "from app.parser.main import apartPage; print(apartPage(['311739319'], dbinsert=True))"
```

## Готово! 🎉

После выполнения всех шагов сервер будет полностью настроен.

