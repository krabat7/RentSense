#!/bin/bash
# Скрипт для обновления парсера на сервере и добавления новых прокси

set -e  # Прерывать при ошибках

echo "================================================================================"
echo "ОБНОВЛЕНИЕ ПАРСЕРА И ДОБАВЛЕНИЕ НОВЫХ ПРОКСИ"
echo "================================================================================"
echo ""

# Цвета
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_ok() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Шаг 1: Переход в директорию проекта
echo "--------------------------------------------------------------------------------"
echo "ШАГ 1: Переход в директорию проекта"
echo "--------------------------------------------------------------------------------"
cd ~/rentsense || cd /root/rentsense
print_ok "Перешли в директорию проекта"
echo ""

# Шаг 2: Обновление кода с GitHub
echo "--------------------------------------------------------------------------------"
echo "ШАГ 2: Обновление кода с GitHub"
echo "--------------------------------------------------------------------------------"
print_info "Выполняем git pull..."
git pull origin main
if [ $? -eq 0 ]; then
    print_ok "Код успешно обновлен"
else
    print_error "Ошибка при обновлении кода"
    exit 1
fi
echo ""

# Шаг 3: Проверка наличия .env
echo "--------------------------------------------------------------------------------"
echo "ШАГ 3: Проверка .env файла"
echo "--------------------------------------------------------------------------------"
if [ ! -f ".env" ]; then
    print_error "Файл .env не найден!"
    exit 1
fi
print_ok "Файл .env найден"

# Создаем бэкап
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
print_ok "Создан бэкап .env"
echo ""

# Шаг 4: Добавление новых прокси
echo "--------------------------------------------------------------------------------"
echo "ШАГ 4: Добавление новых прокси"
echo "--------------------------------------------------------------------------------"

# Новые прокси (формат: IP:PORT@USER:PASS -> http://USER:PASS@IP:PORT)
NEW_PROXIES=(
    "http://h6AQsQ2tp2:5y8yVXZpHx@194.226.239.78:10270"
    "http://dU4HJaeMnS:vWChttfQ9R@194.226.239.64:10270"
    "http://MuHNwZGcSD:LRMf7sBS8h@109.237.106.117:10270"
    "http://vkutfnTtAs:LMeXf6BZee@45.142.208.13:10270"
    "http://vwxUrWbuDn:cbs3Z5XZch@185.42.27.4:10270"
)

# Находим последний номер прокси в .env
LAST_PROXY_NUM=0
while grep -q "^PROXY$((LAST_PROXY_NUM + 1))=" .env; do
    LAST_PROXY_NUM=$((LAST_PROXY_NUM + 1))
done

print_info "Найдено существующих прокси: $LAST_PROXY_NUM"

# Добавляем новые прокси
PROXY_NUM=$((LAST_PROXY_NUM + 1))
for proxy in "${NEW_PROXIES[@]}"; do
    # Проверяем, нет ли уже такого прокси
    if ! grep -q "$proxy" .env; then
        echo "PROXY${PROXY_NUM}=${proxy}" >> .env
        print_ok "Добавлен PROXY${PROXY_NUM}"
        PROXY_NUM=$((PROXY_NUM + 1))
    else
        print_info "Прокси уже существует, пропускаем"
    fi
done

TOTAL_PROXIES=$((PROXY_NUM - 1))
print_ok "Всего прокси в .env: $TOTAL_PROXIES"
echo ""

# Шаг 5: Проверка установленных зависимостей
echo "--------------------------------------------------------------------------------"
echo "ШАГ 5: Проверка зависимостей"
echo "--------------------------------------------------------------------------------"

# Проверяем наличие playwright
if python3 -c "import playwright" 2>/dev/null; then
    print_ok "playwright установлен"
else
    print_error "playwright не установлен!"
    print_info "Установите: pip3 install playwright curl-cffi --break-system-packages"
    exit 1
fi

# Проверяем наличие curl_cffi
if python3 -c "import curl_cffi" 2>/dev/null; then
    print_ok "curl_cffi установлен"
else
    print_error "curl_cffi не установлен!"
    print_info "Установите: pip3 install curl-cffi --break-system-packages"
    exit 1
fi

# Проверяем наличие sqlalchemy
if python3 -c "import sqlalchemy" 2>/dev/null; then
    print_ok "sqlalchemy установлен"
else
    print_error "sqlalchemy не установлен!"
    print_info "Установите: pip3 install sqlalchemy --break-system-packages"
    exit 1
fi

echo ""

# Шаг 6: Проверка структуры проекта
echo "--------------------------------------------------------------------------------"
echo "ШАГ 6: Проверка структуры проекта"
echo "--------------------------------------------------------------------------------"

REQUIRED_FILES=(
    "app/parser/main.py"
    "app/parser/tools.py"
    "app/parser/pagecheck.py"
    "app/parser/database.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_ok "Найден: $file"
    else
        print_error "Не найден: $file"
        exit 1
    fi
done
echo ""

# Шаг 7: Итоговая информация
echo "================================================================================"
echo "ГОТОВО К ЗАПУСКУ!"
echo "================================================================================"
echo ""
print_ok "Код обновлен"
print_ok "Добавлено новых прокси: ${#NEW_PROXIES[@]}"
print_ok "Всего прокси в .env: $TOTAL_PROXIES"
print_ok "Все зависимости установлены"
echo ""
print_info "Для запуска парсера используйте:"
echo "  python3 -m app.parser.main"
echo ""
print_info "Или через scheduler:"
echo "  python3 -m app.scheduler.crontab"
echo ""
print_info "Для просмотра логов:"
echo "  tail -f rentsense.log"
echo ""


