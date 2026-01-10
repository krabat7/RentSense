#!/bin/bash
# Автоматическая настройка сервера через SSH

SERVER_IP="89.110.92.128"
SERVER_USER="root"
SERVER_PASSWORD="D68v9kz3mL21a!FRZm23"
REMOTE_DIR="/root/rentsense"
PROJECT_DIR="F:/hw_hse/Diploma/RentSense"

echo "=== Автоматическая настройка сервера ==="
echo "Сервер: $SERVER_USER@$SERVER_IP"

# Установка sshpass если нужно
if ! command -v sshpass &> /dev/null; then
    echo "Установка sshpass..."
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        echo "Для Windows установите sshpass через WSL или используйте PuTTY"
        exit 1
    else
        sudo apt-get install -y sshpass 2>/dev/null || yum install -y sshpass 2>/dev/null
    fi
fi

# Функция для выполнения SSH команд
ssh_cmd() {
    sshpass -p "$SERVER_PASSWORD" ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_IP} "$1"
}

# Функция для копирования файлов
scp_cmd() {
    sshpass -p "$SERVER_PASSWORD" scp -o StrictHostKeyChecking=no -r "$1" ${SERVER_USER}@${SERVER_IP}:"$2"
}

echo ""
echo "Шаг 1: Проверка подключения..."
ssh_cmd "echo 'Connected successfully'"

echo ""
echo "Шаг 2: Установка Docker..."
ssh_cmd "command -v docker >/dev/null 2>&1 || (curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh && rm get-docker.sh)"

echo ""
echo "Шаг 3: Установка Docker Compose..."
ssh_cmd "command -v docker-compose >/dev/null 2>&1 || (apt update -qq && apt install -y docker-compose)"

echo ""
echo "Шаг 4: Установка системных зависимостей..."
ssh_cmd "apt update -qq && apt install -y libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 wget git"

echo ""
echo "Шаг 5: Создание директорий..."
ssh_cmd "mkdir -p $REMOTE_DIR/logs $REMOTE_DIR/backups $REMOTE_DIR/data/raw $REMOTE_DIR/data/processed"

echo ""
echo "Шаг 6: Копирование файлов..."
cd "$PROJECT_DIR" || cd /mnt/f/hw_hse/Diploma/RentSense || pwd

# Копирование основных файлов
scp_cmd "app" "$REMOTE_DIR/"
scp_cmd "ml" "$REMOTE_DIR/"
scp_cmd "tests" "$REMOTE_DIR/"
scp_cmd "docker-compose.prod.yml" "$REMOTE_DIR/"
scp_cmd "Dockerfile" "$REMOTE_DIR/"
scp_cmd "requirements.txt" "$REMOTE_DIR/"
scp_cmd "create_database.py" "$REMOTE_DIR/"
scp_cmd ".env.server" "$REMOTE_DIR/.env"

# Копирование скриптов
for file in *.sh; do
    if [ -f "$file" ]; then
        scp_cmd "$file" "$REMOTE_DIR/"
    fi
done

echo ""
echo "Шаг 7: Настройка прав доступа..."
ssh_cmd "cd $REMOTE_DIR && chmod +x *.sh"

echo ""
echo "=== Подготовка завершена ==="
echo ""
echo "⚠️  ВАЖНО: Настройте пароли в .env на сервере!"
echo ""
echo "Выполните на сервере:"
echo "ssh $SERVER_USER@$SERVER_IP"
echo "cd $REMOTE_DIR"
echo "nano .env  # Замените CHANGE_THIS_TO_STRONG_PASSWORD"
echo "docker-compose -f docker-compose.prod.yml up -d --build"
echo "sleep 60 && docker-compose exec backend python -m app.parser.init_db"

