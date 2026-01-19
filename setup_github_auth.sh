#!/bin/bash
# Скрипт для настройки аутентификации GitHub на сервере
# Использование: ./setup_github_auth.sh

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Настройка аутентификации GitHub ===${NC}"
echo ""

# Вариант 1: SSH ключи (рекомендуется)
echo -e "${GREEN}Вариант 1: Настройка через SSH ключи (рекомендуется)${NC}"
echo ""
read -p "Настроить SSH ключи? (y/n): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Проверяем, есть ли уже SSH ключ
    if [ -f ~/.ssh/id_rsa.pub ]; then
        echo -e "${YELLOW}SSH ключ уже существует${NC}"
        echo "Публичный ключ:"
        cat ~/.ssh/id_rsa.pub
        echo ""
        echo "Скопируйте этот ключ и добавьте в GitHub:"
        echo "  https://github.com/settings/keys -> New SSH key"
    else
        echo "Генерация SSH ключа..."
        ssh-keygen -t ed25519 -C "server@rentsense" -f ~/.ssh/id_rsa -N ""
        echo -e "${GREEN}SSH ключ создан${NC}"
        echo ""
        echo "Публичный ключ:"
        cat ~/.ssh/id_rsa.pub
        echo ""
        echo -e "${YELLOW}Скопируйте этот ключ и добавьте в GitHub:${NC}"
        echo "  https://github.com/settings/keys -> New SSH key"
        echo ""
        read -p "Нажмите Enter после добавления ключа в GitHub..."
    fi
    
    # Меняем remote URL на SSH
    CURRENT_REMOTE=$(git remote get-url origin)
    if [[ $CURRENT_REMOTE == https://* ]]; then
        echo "Изменение remote URL на SSH..."
        git remote set-url origin git@github.com:krabat7/RentSense.git
        echo -e "${GREEN}Remote URL изменен на SSH${NC}"
    else
        echo -e "${GREEN}Remote уже использует SSH${NC}"
    fi
    
    # Тестируем подключение
    echo "Тестирование SSH подключения..."
    if ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
        echo -e "${GREEN}SSH подключение работает!${NC}"
    else
        echo -e "${YELLOW}SSH подключение требует настройки${NC}"
        echo "Убедитесь, что вы добавили SSH ключ в GitHub"
    fi
fi

echo ""
echo -e "${BLUE}=== Вариант 2: Personal Access Token ===${NC}"
echo ""
read -p "Настроить через Personal Access Token? (y/n): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Для использования Personal Access Token:"
    echo "1. Создайте токен: https://github.com/settings/tokens"
    echo "2. Выберите права: repo (все права на репозиторий)"
    echo "3. Скопируйте токен"
    echo ""
    read -p "Введите Personal Access Token: " -s TOKEN
    echo ""
    
    if [ -n "$TOKEN" ]; then
        # Меняем remote URL на HTTPS с токеном
        git remote set-url origin "https://${TOKEN}@github.com/krabat7/RentSense.git"
        echo -e "${GREEN}Remote URL обновлен с токеном${NC}"
        
        # Тестируем
        echo "Тестирование подключения..."
        if git fetch origin main > /dev/null 2>&1; then
            echo -e "${GREEN}Подключение работает!${NC}"
        else
            echo -e "${RED}Ошибка подключения. Проверьте токен.${NC}"
        fi
    fi
fi

echo ""
echo -e "${GREEN}=== Настройка завершена ===${NC}"
echo ""
echo "Текущий remote URL:"
git remote get-url origin | sed 's/\(.*:\/\/\).*@\(.*\)/\1***@\2/'

