#!/bin/bash
# Быстрая настройка сервера на VDSina

set -e

echo "=== Настройка сервера RentSense ==="
echo ""

# Проверка, что мы root
if [ "$EUID" -ne 0 ]; then 
    echo "Пожалуйста, запустите от root"
    exit 1
fi

echo "Шаг 1: Обновление системы..."
apt update && apt upgrade -y

echo ""
echo "Шаг 2: Установка Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
else
    echo "Docker уже установлен"
fi

echo ""
echo "Шаг 3: Установка Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    apt install docker-compose -y
else
    echo "Docker Compose уже установлен"
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
    curl

echo ""
echo "Шаг 5: Проверка установки..."
docker --version
docker-compose --version

echo ""
echo "=== Установка завершена ==="
echo ""
echo "Следующие шаги:"
echo "1. Загрузите проект на сервер (git clone или scp)"
echo "2. Настройте .env файл (см. SETUP_VDSINA.md)"
echo "3. Запустите: docker-compose -f docker-compose.prod.yml up -d --build"
echo "4. Инициализируйте БД: docker-compose exec backend python -m app.parser.init_db"

