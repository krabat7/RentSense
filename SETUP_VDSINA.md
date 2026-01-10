# Инструкция по настройке вашего сервера на VDSina

## Информация о сервере

- **IP:** 89.110.92.128
- **Hostname:** v3017595.hosted-by-vdsina.ru
- **ОС:** Ubuntu 24.04
- **Ресурсы:** 1 core / 1 GB RAM / 10 GB диск
- **Локация:** Москва, Россия

## Шаг 1: Подключение к серверу

```bash
ssh root@89.110.92.128
# Введите пароль, который пришел на email
```

## Шаг 2: Установка Docker и Docker Compose

```bash
# Обновление системы
apt update && apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Установка Docker Compose
apt install docker-compose -y

# Проверка
docker --version
docker-compose --version
```

## Шаг 3: Установка системных зависимостей для Playwright

```bash
apt install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    wget \
    git
```

## Шаг 4: Загрузка проекта на сервер

### Вариант А: Через Git (если репозиторий есть)

```bash
git clone <your-repo-url> rentsense
cd rentsense
```

### Вариант Б: Через SCP с локальной машины (Windows PowerShell)

```powershell
# В PowerShell на вашем компьютере
cd F:\hw_hse\Diploma\RentSense

# Создать архив (исключая ненужные файлы)
tar -czf rentsense.tar.gz --exclude='ocenomet' --exclude='__pycache__' --exclude='*.pyc' --exclude='*.html' --exclude='*.log' --exclude='.env' app/ ml/ tests/ docker-compose.prod.yml Dockerfile requirements.txt *.md *.sh *.py pyproject.toml

# Загрузить на сервер
scp rentsense.tar.gz root@89.110.92.128:/root/

# На сервере распаковать
ssh root@89.110.92.128
cd /root
tar -xzf rentsense.tar.gz -C rentsense --strip-components=0 || mkdir rentsense && tar -xzf rentsense.tar.gz -C rentsense
cd rentsense
```

## Шаг 5: Настройка .env файла

```bash
cd /root/rentsense
nano .env
```

Содержимое `.env`:

```env
DB_TYPE=mysql+pymysql
DB_LOGIN=root
DB_PASS=YOUR_STRONG_PASSWORD_HERE
DB_IP=mysql
DB_PORT=3306
DB_NAME=rentsense

MYSQL_ROOT_PASSWORD=YOUR_STRONG_PASSWORD_HERE
MYSQL_PASSWORD=rentsense

PROXY1=http://gPrh7mayd7:cDs82GsH8e@46.161.29.91:31638
PROXY2=http://gF5CdZ3tVh:WBF5P4a7uW@46.161.29.212:36095
PROXY3=http://Y34xbQACPJ:pQVJx66wc2@83.171.240.229:32844
PROXY4=http://Tz8am3:EY5U7F@209.127.142.50:9709
PROXY5=http://Tz8am3:EY5U7F@168.196.238.113:9267

BACKUP_TYPE=yandex
YANDEX_ACCESS_KEY=YCAJEhxLcNZ_zudb0rzs9Vo7o
YANDEX_SECRET_KEY=YCONmXbp4fD1YH_p_lb547nc0Le2UXfy6F_3-8nq
YANDEX_BUCKET=rentsense-bucket

MLFLOW_TRACKING_URI=http://localhost:5000
```

**Важно:** Замените `YOUR_STRONG_PASSWORD_HERE` на надежный пароль!

## Шаг 6: Запуск сервисов

```bash
# Сборка и запуск
docker-compose -f docker-compose.prod.yml up -d --build

# Проверка статуса
docker-compose -f docker-compose.prod.yml ps

# Просмотр логов
docker-compose -f docker-compose.prod.yml logs -f
```

## Шаг 7: Инициализация БД

```bash
# Создание БД
docker-compose -f docker-compose.prod.yml exec backend python create_database.py

# Создание таблиц
docker-compose -f docker-compose.prod.yml exec backend python -m app.parser.init_db

# Проверка таблиц
docker-compose -f docker-compose.prod.yml exec mysql mysql -uroot -pYOUR_STRONG_PASSWORD_HERE rentsense -e "SHOW TABLES;"
```

## Шаг 8: Настройка автоматических бэкапов

```bash
# Сделать скрипт исполняемым
chmod +x backup_to_cloud.sh
mv backup_to_cloud.sh backup_db.sh

# Создать директорию для логов
mkdir -p logs

# Добавить в cron (ежедневно в 3:00)
(crontab -l 2>/dev/null; echo "0 3 * * * cd /root/rentsense && ./backup_db.sh >> logs/backup.log 2>&1") | crontab -

# Проверить cron
crontab -l

# Тестовый бэкап
./backup_db.sh
```

## Шаг 9: Тест парсера

```bash
# Тест парсинга одного объявления
docker-compose -f docker-compose.prod.yml exec backend python -c "
from app.parser.main import apartPage
result = apartPage(['311739319'], dbinsert=True)
print('Result:', result)
"

# Проверка данных в БД
docker-compose -f docker-compose.prod.yml exec mysql mysql -uroot -pYOUR_STRONG_PASSWORD_HERE rentsense -e "SELECT COUNT(*) as total_offers FROM offers;"
```

## Шаг 10: Запуск автоматического парсинга (опционально)

```bash
# Парсер будет работать в контейнере parser по расписанию (настроено в crontab.py)
# Или можно запустить вручную:

docker-compose -f docker-compose.prod.yml exec backend python -c "
from app.parser.main import listPages, apartPage
for page in range(1, 10):
    ids = listPages(page)
    if ids == 'END':
        break
    apartPage(ids, dbinsert=True)
    print(f'Page {page} done')
"
```

## Полезные команды

### Просмотр логов
```bash
# Все сервисы
docker-compose -f docker-compose.prod.yml logs -f

# Конкретный сервис
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f parser
docker-compose -f docker-compose.prod.yml logs -f mysql
```

### Мониторинг ресурсов
```bash
# Использование ресурсов
docker stats

# Память
free -h

# Диск
df -h
```

### Остановка/перезапуск
```bash
# Остановка
docker-compose -f docker-compose.prod.yml down

# Запуск
docker-compose -f docker-compose.prod.yml up -d

# Перезапуск
docker-compose -f docker-compose.prod.yml restart
```

### Проверка бэкапов
```bash
# Локальные бэкапы
ls -lh backups/

# Облачные бэкапы (Yandex)
docker run --rm \
    -e AWS_ACCESS_KEY_ID=YCAJEhxLcNZ_zudb0rzs9Vo7o \
    -e AWS_SECRET_ACCESS_KEY=YCONmXbp4fD1YH_p_lb547nc0Le2UXfy6F_3-8nq \
    amazon/aws-cli s3 ls s3://rentsense-bucket/rentsense/ \
    --endpoint-url=https://storage.yandexcloud.net
```

## Проверка после настройки

```bash
# 1. Все контейнеры запущены
docker-compose -f docker-compose.prod.yml ps

# 2. БД работает
docker-compose -f docker-compose.prod.yml exec mysql mysqladmin ping -h localhost -uroot -pYOUR_STRONG_PASSWORD_HERE

# 3. Парсер работает
docker-compose -f docker-compose.prod.yml exec backend python test_full_parse.py 311739319

# 4. Бэкап работает
./backup_db.sh
```

## Что дальше?

После успешной настройки:
1. Начать собирать данные (запустить парсер)
2. Мониторить использование ресурсов
3. При необходимости увеличить тариф (2 GB RAM)

