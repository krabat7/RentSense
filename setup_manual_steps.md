# Ручная настройка сервера (пошагово)

## Сервер и пароль
- **IP:** 89.110.92.128
- **User:** root
- **Password:** D68v9kz3mL21a!FRZm23

## Шаг 1: Подключение к серверу

```powershell
ssh root@89.110.92.128
# Введите пароль: D68v9kz3mL21a!FRZm23
```

## Шаг 2: Установка Docker (на сервере)

```bash
apt update
apt install -y curl git
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
rm get-docker.sh
apt install -y docker-compose
```

## Шаг 3: Установка системных зависимостей

```bash
apt install -y libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 wget
```

## Шаг 4: Создание директорий

```bash
mkdir -p /root/rentsense/logs /root/rentsense/backups /root/rentsense/data/raw /root/rentsense/data/processed
```

## Шаг 5: Копирование файлов (на вашем компьютере)

Откройте **новый терминал PowerShell** (оставьте SSH подключение открытым в другом окне) и выполните:

```powershell
cd F:\hw_hse\Diploma\RentSense

# Копирование файлов (потребуется ввести пароль несколько раз)
scp -r app root@89.110.92.128:/root/rentsense/
scp -r ml root@89.110.92.128:/root/rentsense/
scp -r tests root@89.110.92.128:/root/rentsense/
scp docker-compose.prod.yml root@89.110.92.128:/root/rentsense/
scp Dockerfile root@89.110.92.128:/root/rentsense/
scp requirements.txt root@89.110.92.128:/root/rentsense/
scp create_database.py root@89.110.92.128:/root/rentsense/
scp .env.server root@89.110.92.128:/root/rentsense/.env
```

## Шаг 6: Настройка на сервере

Вернитесь в SSH сессию на сервере:

```bash
cd /root/rentsense
mv .env.server .env 2>/dev/null || true
chmod +x *.sh
nano .env
```

В nano замените `CHANGE_THIS_TO_STRONG_PASSWORD` (2 раза) на надежный пароль, затем:
- Ctrl+X
- Y
- Enter

## Шаг 7: Запуск Docker Compose

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

Подождите 60-90 секунд пока MySQL запустится.

## Шаг 8: Инициализация БД

```bash
sleep 60
docker-compose -f docker-compose.prod.yml exec backend python create_database.py
docker-compose -f docker-compose.prod.yml exec backend python -m app.parser.init_db
```

## Шаг 9: Проверка

```bash
# Проверка контейнеров
docker-compose -f docker-compose.prod.yml ps

# Проверка БД
docker-compose -f docker-compose.prod.yml exec mysql mysql -uroot -pYOUR_PASSWORD rentsense -e "SHOW TABLES;"

# Тест парсера
docker-compose -f docker-compose.prod.yml exec backend python -c "from app.parser.main import apartPage; print(apartPage(['311739319'], dbinsert=True))"
```

## Готово!

После этого сервер настроен и готов к работе.

