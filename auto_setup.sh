#!/bin/bash
# Автоматическая настройка всего проекта на сервере VDSina

set -e

echo "=========================================="
echo "  RentSense - Автоматическая настройка"
echo "=========================================="
echo ""

# Проверка, что мы root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Запустите от root"
    exit 1
fi

# Переход в рабочую директорию
cd /root/rentsense || {
    echo "ERROR: Директория /root/rentsense не найдена"
    echo "Убедитесь, что проект загружен на сервер"
    exit 1
}

echo "Шаг 1: Обновление системы..."
apt update && apt upgrade -y

echo ""
echo "Шаг 2: Установка Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
else
    echo "  Docker уже установлен"
fi

echo ""
echo "Шаг 3: Установка Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    apt install docker-compose -y
else
    echo "  Docker Compose уже установлен"
fi

echo ""
echo "Шаг 4: Установка системных зависимостей..."
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
    git \
    curl \
    awscli 2>/dev/null || echo "  awscli будет установлен через Docker"

echo ""
echo "Шаг 5: Проверка .env файла..."
if [ ! -f .env ]; then
    if [ -f .env.server ]; then
        echo "  Копирование .env.server в .env"
        cp .env.server .env
    else
        echo "ERROR: Файл .env не найден!"
        echo "Создайте .env из .env.example или .env.server"
        exit 1
    fi
fi

# Проверка паролей в .env
if grep -q "CHANGE_THIS_TO_STRONG_PASSWORD" .env; then
    echo ""
    echo "⚠️  ВНИМАНИЕ: В .env есть незамененные пароли!"
    echo "Замените 'CHANGE_THIS_TO_STRONG_PASSWORD' на надежный пароль"
    echo ""
    read -p "Продолжить с настройкой паролей? (yes/no): " CONT
    
    if [ "$CONT" != "yes" ]; then
        echo "Отменено. Отредактируйте .env: nano .env"
        exit 0
    fi
    
    # Генерация случайного пароля
    NEW_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    echo "Генерирую пароль: $NEW_PASSWORD"
    
    # Замена паролей
    sed -i "s/CHANGE_THIS_TO_STRONG_PASSWORD/$NEW_PASSWORD/g" .env
    echo "  Пароли обновлены в .env"
    echo "  ⚠️  СОХРАНИТЕ ЭТОТ ПАРОЛЬ: $NEW_PASSWORD"
fi

# Загрузка переменных из .env
export $(grep -v '^#' .env | xargs)

echo ""
echo "Шаг 6: Создание директорий..."
mkdir -p logs backups data/raw data/processed

echo ""
echo "Шаг 7: Сборка и запуск Docker контейнеров..."
docker-compose -f docker-compose.prod.yml pull 2>/dev/null || true
docker-compose -f docker-compose.prod.yml build

echo ""
echo "Шаг 8: Запуск сервисов..."
docker-compose -f docker-compose.prod.yml up -d

echo ""
echo "Ожидание запуска MySQL (60 секунд)..."
sleep 60

# Проверка здоровья MySQL
echo ""
echo "Шаг 9: Проверка MySQL..."
MAX_RETRIES=30
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    if docker-compose -f docker-compose.prod.yml exec -T mysql mysqladmin ping -h localhost -uroot -p${MYSQL_ROOT_PASSWORD} --silent 2>/dev/null; then
        echo "  MySQL запущен!"
        break
    fi
    RETRY=$((RETRY+1))
    echo "  Ожидание MySQL... ($RETRY/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo "  WARNING: MySQL не ответил, продолжаем..."
fi

echo ""
echo "Шаг 10: Инициализация БД..."
docker-compose -f docker-compose.prod.yml exec -T backend python create_database.py 2>/dev/null || {
    echo "  Создание БД через MySQL напрямую..."
    docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "CREATE DATABASE IF NOT EXISTS rentsense CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null || true
}

docker-compose -f docker-compose.prod.yml exec -T backend python -m app.parser.init_db || {
    echo "  WARNING: init_db завершился с ошибкой, проверьте логи"
}

echo ""
echo "Шаг 11: Настройка бэкапов..."
chmod +x backup_to_cloud.sh 2>/dev/null || true
if [ -f backup_to_cloud.sh ]; then
    cp backup_to_cloud.sh backup_db.sh
    chmod +x backup_db.sh
    
    # Добавление в cron
    (crontab -l 2>/dev/null | grep -v "backup_db.sh" || true; echo "0 3 * * * cd /root/rentsense && ./backup_db.sh >> logs/backup.log 2>&1") | crontab -
    echo "  Бэкапы настроены (ежедневно в 3:00)"
    
    # Тестовый бэкап
    echo "  Тестовый бэкап..."
    ./backup_db.sh 2>&1 | head -20 || echo "  WARNING: Тестовый бэкап не удался"
fi

echo ""
echo "Шаг 12: Проверка установки..."
echo ""
echo "Статус контейнеров:"
docker-compose -f docker-compose.prod.yml ps

echo ""
echo "Проверка таблиц БД:"
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -p${MYSQL_ROOT_PASSWORD} rentsense -e "SHOW TABLES;" 2>/dev/null | head -10 || echo "  WARNING: Не удалось проверить таблицы"

echo ""
echo "=========================================="
echo "  ✓ Настройка завершена!"
echo "=========================================="
echo ""
echo "Что дальше:"
echo "1. Проверить статус: docker-compose -f docker-compose.prod.yml ps"
echo "2. Просмотреть логи: docker-compose -f docker-compose.prod.yml logs -f"
echo "3. Тест парсера: docker-compose exec backend python test_full_parse.py 311739319"
echo ""
echo "Пароли:"
echo "  MySQL root: ${MYSQL_ROOT_PASSWORD}"
echo "  Сохраните в надежном месте!"
echo ""
echo "Бэкапы:"
echo "  Локальные: ./backups/"
echo "  Облачные: s3://rentsense-bucket/rentsense/ (Yandex Object Storage)"
echo ""
echo "Полезные команды:"
echo "  Логи: docker-compose -f docker-compose.prod.yml logs -f"
echo "  Перезапуск: docker-compose -f docker-compose.prod.yml restart"
echo "  Остановка: docker-compose -f docker-compose.prod.yml down"
echo ""

