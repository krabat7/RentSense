#!/bin/bash
# Скрипт для настройки автоматического pull на сервере
# Использование: ./setup_auto_pull.sh

set -e

echo "=== Настройка автоматического pull на сервере ==="

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка, что скрипт запущен на сервере
if [ ! -d ".git" ]; then
    echo -e "${YELLOW}Внимание: .git директория не найдена. Убедитесь, что вы в корне проекта.${NC}"
    read -p "Продолжить? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Определяем путь к проекту (текущая директория)
PROJECT_DIR=$(pwd)
echo -e "${GREEN}Директория проекта: $PROJECT_DIR${NC}"

# Копируем скрипт git-pull-hook.sh, если он есть
if [ -f "git-pull-hook.sh" ]; then
    cp git-pull-hook.sh "$PROJECT_DIR/git-pull-hook.sh"
    chmod +x "$PROJECT_DIR/git-pull-hook.sh"
    echo -e "${GREEN}Скрипт git-pull-hook.sh скопирован${NC}"
fi

# Вариант 1: Настройка через cron (простой способ)
echo ""
echo "=== Вариант 1: Настройка через cron (каждые 5 минут) ==="
# Используем скрипт, если он есть, иначе простой git pull
if [ -f "$PROJECT_DIR/git-pull-hook.sh" ]; then
    CRON_JOB="*/5 * * * * $PROJECT_DIR/git-pull-hook.sh >> /var/log/git-pull.log 2>&1"
else
    CRON_JOB="*/5 * * * * cd $PROJECT_DIR && /usr/bin/git pull origin main >> /var/log/git-pull.log 2>&1"
fi

# Проверяем, есть ли уже такая задача в crontab
if crontab -l 2>/dev/null | grep -q "git pull origin main"; then
    echo -e "${YELLOW}Задача git pull уже существует в crontab${NC}"
    read -p "Заменить? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Удаляем старую задачу
        crontab -l 2>/dev/null | grep -v "git pull origin main" | crontab -
        # Добавляем новую
        (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
        echo -e "${GREEN}Задача обновлена в crontab${NC}"
    fi
else
    # Добавляем новую задачу
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo -e "${GREEN}Задача добавлена в crontab${NC}"
fi

# Создаем директорию для логов, если её нет
sudo mkdir -p /var/log
sudo touch /var/log/git-pull.log
sudo chmod 666 /var/log/git-pull.log

# Вариант 2: Настройка через GitHub webhook (более продвинутый)
echo ""
echo "=== Вариант 2: Настройка через GitHub webhook ==="
echo "Для настройки webhook нужно:"
echo "1. Установить webhook сервер (например, webhook или simple-webhook)"
echo "2. Создать endpoint для получения webhook от GitHub"
echo "3. Настроить webhook в настройках GitHub репозитория"
echo ""
read -p "Настроить webhook сейчас? (y/n): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Проверяем, установлен ли webhook
    if ! command -v webhook &> /dev/null; then
        echo "Установка webhook..."
        # Для Ubuntu/Debian
        if command -v apt-get &> /dev/null; then
            wget https://github.com/adnanh/webhook/releases/latest/download/webhook-linux-amd64.tar.gz
            tar -xzf webhook-linux-amd64.tar.gz
            sudo mv webhook-linux-amd64/webhook /usr/local/bin/
            rm -rf webhook-linux-amd64*
        fi
    fi
    
    # Создаем директорию для hooks
    mkdir -p "$PROJECT_DIR/hooks"
    
    # Создаем скрипт для обработки webhook
    cat > "$PROJECT_DIR/hooks/git-pull.sh" << 'EOF'
#!/bin/bash
cd /root/RentSense  # Измените путь на ваш
git pull origin main
# Перезапустить контейнеры, если нужно
# cd /root/RentSense && docker-compose -f docker-compose.prod.yml restart
EOF
    
    chmod +x "$PROJECT_DIR/hooks/git-pull.sh"
    
    # Создаем конфигурацию webhook
    cat > "$PROJECT_DIR/hooks.json" << EOF
[
  {
    "id": "git-pull",
    "execute-command": "$PROJECT_DIR/hooks/git-pull.sh",
    "command-working-directory": "$PROJECT_DIR"
  }
]
EOF
    
    echo -e "${GREEN}Webhook настроен${NC}"
    echo "Для запуска webhook сервера выполните:"
    echo "  webhook -hooks hooks.json -verbose -port 9000"
    echo ""
    echo "Затем добавьте webhook в GitHub:"
    echo "  URL: http://your-server-ip:9000/hooks/git-pull"
    echo "  Content type: application/json"
fi

echo ""
echo -e "${GREEN}=== Настройка завершена ===${NC}"
echo ""
echo "Текущие задачи crontab:"
crontab -l 2>/dev/null | grep "git pull" || echo "Нет задач git pull"
echo ""
echo "Для просмотра логов: tail -f /var/log/git-pull.log"

