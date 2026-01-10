# Инструкция по развертыванию на сервере

## Требования

- Сервер с Ubuntu 20.04+ (или другой Linux)
- Docker и Docker Compose установлены
- Минимум 2GB RAM, 20GB диск

## Варианты серверов

### 1. Hetzner Cloud (рекомендуется)
- Цена: от ~500₽/мес (4GB RAM)
- Регистрация: https://hetzner.com/cloud
- Выбрать: CPX11 или больше

### 2. Selectel
- Цена: от ~800₽/мес
- Регистрация: https://selectel.ru/vps/

### 3. Yandex Cloud
- Цена: от ~1000₽/мес
- Регистрация: https://cloud.yandex.ru/

## Установка на сервере

### 1. Подключение к серверу

```bash
ssh root@your-server-ip
```

### 2. Установка Docker и Docker Compose

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

### 3. Клонирование репозитория

```bash
# Установка Git
apt install git -y

# Клонирование (или загрузка проекта)
git clone <your-repo-url> rentsense
cd rentsense

# Или загрузка через scp с локальной машины:
# scp -r ./RentSense root@your-server-ip:/root/rentsense
```

### 4. Настройка переменных окружения

```bash
# Создание .env файла
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

MLFLOW_TRACKING_URI=http://localhost:5000
```

### 5. Установка зависимостей системы

```bash
# Для Playwright нужны системные библиотеки
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
    libasound2
```

### 6. Запуск сервисов

```bash
# Сборка и запуск
docker-compose -f docker-compose.prod.yml up -d --build

# Проверка статуса
docker-compose -f docker-compose.prod.yml ps

# Просмотр логов
docker-compose -f docker-compose.prod.yml logs -f
```

### 7. Инициализация БД

```bash
# Вход в контейнер
docker-compose -f docker-compose.prod.yml exec backend bash

# Инициализация БД
python -m app.parser.init_db

# Создание таблиц
python create_database.py

# Выход
exit
```

### 8. Настройка бэкапов БД

```bash
# Создание директории для бэкапов
mkdir -p backups

# Создание скрипта бэкапа
cat > /root/backup_db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/root/rentsense/backups"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="rentsense_backup_${DATE}.sql"

docker-compose -f /root/rentsense/docker-compose.prod.yml exec -T mysql \
    mysqldump -uroot -p${MYSQL_ROOT_PASSWORD} rentsense > ${BACKUP_DIR}/${FILENAME}

# Сжатие
gzip ${BACKUP_DIR}/${FILENAME}

# Удаление старых бэкапов (старше 7 дней)
find ${BACKUP_DIR} -name "*.sql.gz" -mtime +7 -delete

echo "Backup created: ${FILENAME}.gz"
EOF

chmod +x /root/backup_db.sh

# Добавление в cron (каждый день в 3:00)
(crontab -l 2>/dev/null; echo "0 3 * * * /root/backup_db.sh") | crontab -
```

## Управление

### Запуск/остановка

```bash
# Запуск
docker-compose -f docker-compose.prod.yml up -d

# Остановка
docker-compose -f docker-compose.prod.yml down

# Перезапуск
docker-compose -f docker-compose.prod.yml restart
```

### Просмотр логов

```bash
# Все сервисы
docker-compose -f docker-compose.prod.yml logs -f

# Конкретный сервис
docker-compose -f docker-compose.prod.yml logs -f parser
docker-compose -f docker-compose.prod.yml logs -f backend
```

### Запуск парсера вручную

```bash
docker-compose -f docker-compose.prod.yml exec backend python -c "
from app.parser.main import listPages, apartPage
for page in range(1, 10):
    ids = listPages(page)
    if ids == 'END':
        break
    apartPage(ids, dbinsert=True)
"
```

### Подключение к БД

```bash
docker-compose -f docker-compose.prod.yml exec mysql mysql -uroot -p rentsense
```

## Мониторинг

### Проверка использования ресурсов

```bash
docker stats
```

### Проверка дискового пространства

```bash
df -h
docker system df
```

## Безопасность

1. **Измените пароли** в `.env` файле
2. **Настройте firewall**:
   ```bash
   ufw allow 22/tcp
   ufw allow 8000/tcp
   ufw enable
   ```
3. **Регулярные обновления**:
   ```bash
   apt update && apt upgrade -y
   ```

## Восстановление из бэкапа

```bash
# Распаковка
gunzip backups/rentsense_backup_YYYYMMDD_HHMMSS.sql.gz

# Восстановление
docker-compose -f docker-compose.prod.yml exec -T mysql \
    mysql -uroot -p${MYSQL_ROOT_PASSWORD} rentsense < backups/rentsense_backup_YYYYMMDD_HHMMSS.sql
```

