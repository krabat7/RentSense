#!/bin/bash
# Скрипт для автоматического pull с перезапуском контейнеров
# Используется в cron или webhook

set -e

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Директория проекта
PROJECT_DIR="/root/RentSense"
LOG_FILE="/var/log/git-pull.log"

# Функция для логирования
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== Начало обновления проекта ==="

# Переходим в директорию проекта
cd "$PROJECT_DIR" || {
    log "${RED}Ошибка: не удалось перейти в директорию $PROJECT_DIR${NC}"
    exit 1
}

# Сохраняем текущий коммит
OLD_COMMIT=$(git rev-parse HEAD)
log "Текущий коммит: $OLD_COMMIT"

# Сбрасываем локальные изменения в игнорируемых файлах (логи и т.д.)
log "Сброс локальных изменений в игнорируемых файлах..."
git checkout -- . 2>/dev/null || true
git clean -fd --quiet || true

# Получаем последние изменения
log "Получение изменений из репозитория..."
git fetch origin main

# Проверяем, есть ли новые коммиты
NEW_COMMIT=$(git rev-parse origin/main)

if [ "$OLD_COMMIT" = "$NEW_COMMIT" ]; then
    log "${GREEN}Изменений нет, обновление не требуется${NC}"
    exit 0
fi

log "${YELLOW}Обнаружены новые изменения${NC}"
log "Новый коммит: $NEW_COMMIT"

# Делаем pull
log "Выполнение git pull..."
if git pull origin main; then
    log "${GREEN}Git pull выполнен успешно${NC}"
else
    log "${RED}Ошибка при выполнении git pull${NC}"
    exit 1
fi

# Проверяем, изменились ли requirements.txt или Dockerfile
CHANGED_FILES=$(git diff --name-only "$OLD_COMMIT" "$NEW_COMMIT")

if echo "$CHANGED_FILES" | grep -qE "(requirements.txt|Dockerfile|docker-compose)"; then
    log "${YELLOW}Обнаружены изменения в зависимостях или Docker конфигурации${NC}"
    log "Пересборка и перезапуск контейнеров..."
    
    cd "$PROJECT_DIR"
    docker-compose -f docker-compose.prod.yml down
    docker-compose -f docker-compose.prod.yml up -d --build
    
    log "${GREEN}Контейнеры пересобраны и перезапущены${NC}"
elif echo "$CHANGED_FILES" | grep -qE "\.(py|yaml|yml)$"; then
    log "${YELLOW}Обнаружены изменения в Python коде${NC}"
    log "Перезапуск контейнеров..."
    
    cd "$PROJECT_DIR"
    docker-compose -f docker-compose.prod.yml restart
    
    log "${GREEN}Контейнеры перезапущены${NC}"
else
    log "${GREEN}Изменения не требуют перезапуска контейнеров${NC}"
fi

log "${GREEN}=== Обновление завершено успешно ===${NC}"
exit 0

